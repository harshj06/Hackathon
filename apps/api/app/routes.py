"""Learning and companion routes; transactions serialize local economic writes."""
import json
import os
import secrets
from datetime import timedelta
from typing import Literal
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from .storage import Attempt, Mastery, Reward, Inventory, TopicRequest, Chat, Activity, Preference, Receipt, Learner, GeneratedPack, AIUsage, utcnow
from .content import PACKS, COSMETICS, public_pack, Pack
from .learning import get_pack, state, respond, award, india_date
from .companion import guided_reply, privacy_check, CompatibleProvider, online_ready, safe_explain, draft_course
from .security import limit

class TopicInput(BaseModel):
    topic: str = Field(min_length=2, max_length=160)

class StartInput(BaseModel):
    topic: str
    mode: Literal['battle','puzzle','match','boss','timed','placement'] = 'battle'

class AnswerInput(BaseModel):
    sequence: int = Field(ge=0, le=50)
    answer: list[str] = Field(min_length=1, max_length=10)
    key: str = Field(min_length=10, max_length=100)

class ChatInput(BaseModel):
    topic: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=1000)

class PurchaseInput(BaseModel):
    cosmetic: str

class SettingsInput(BaseModel):
    theme: Literal['dark','light'] = 'dark'
    motion: bool = True
    sound: bool = False
    readable: bool = False
    leaderboard: bool = False

def summary(session, learner):
    rewards = list(session.scalars(select(Reward).where(Reward.learner_id==learner.id)))
    xp = sum(r.xp for r in rewards)
    days = {india_date(r.created) for r in rewards if r.xp>0}
    today = india_date()
    day = today if today in days else today-timedelta(days=1)
    streak = 0
    while day in days:
        streak+=1
        day-=timedelta(days=1)
    rows = list(session.scalars(select(Mastery).where(Mastery.learner_id==learner.id)))
    skills = [dict(topic=m.topic,title=PACKS[m.topic].title,accuracy=round(sum(m.evidence.values())/max(1,len(m.evidence))*100),evidence=len(m.evidence),due=m.due.isoformat(),ready=m.due<=utcnow()) for m in rows if m.topic in PACKS]
    rounds = session.scalar(select(func.count()).select_from(Attempt).where(Attempt.learner_id==learner.id,Attempt.completed.is_(True)))
    activity = session.get(Activity, learner.id)
    badges = [title for title,condition in [('First adventure',rounds>0),('Explorer',rounds>=5),('Century',xp>=100),('Three-day spark',streak>=3),('Strong foundations',any(s['accuracy']>=80 and s['evidence']>=4 for s in skills))] if condition]
    return dict(xp=xp,coins=sum(r.coins for r in rewards),level=1+xp//100,streak=streak,today=sum(r.xp for r in rewards if india_date(r.created)==today),goal=40,rounds=rounds,skills=skills,badges=badges,active_minutes=round((activity.seconds if activity else 0)/60,1),equipped=learner.equipped)

def install_routes(app, db, current, owned):
    @app.get('/api/v1/topics')
    def topics(q: str='', account=Depends(current)):
        return [public_pack(p) for p in PACKS.values() if q.lower() in (p.title+' '+p.category+' '+p.id).lower()]

    @app.post('/api/v1/learners/{lid}/topic-requests')
    def request_topic(lid: str, body: TopicInput, account=Depends(current), session=Depends(db)):
        owned(session,account,lid)
        if privacy_check(body.topic):
            raise HTTPException(422,'Enter a topic without personal details.')
        found = next((p for p in PACKS.values() if body.topic.strip().lower() in (p.id,p.title.lower())),None)
        if found:
            return dict(status='ready',topic=public_pack(found))
        previous = session.scalar(select(TopicRequest).where(TopicRequest.learner_id==lid,TopicRequest.topic==body.topic.strip()))
        if not previous:
            previous = TopicRequest(learner_id=lid,topic=body.topic.strip())
            session.add(previous)
            session.flush()
        if online_ready() and previous.status=='awaiting_configuration':
            limit('generate:'+lid,3)
            provider=CompatibleProvider()
            try:
                pack=draft_course(provider,body.topic)
            except Exception:
                raise HTTPException(502,'The course could not be safely generated. Please try again later.')
            pack.id='custom-'+previous.id
            session.add(GeneratedPack(request_id=previous.id,payload=pack.model_dump()))
            session.add(AIUsage(learner_id=lid,operation='course',tokens=provider.tokens,model=os.getenv('AI_MODEL','')))
            previous.status='review_required'
        if previous.status=='review_required':
            return dict(id=previous.id,status=previous.status,message='Your course draft is ready for content review. It will appear as a world once approved.')
        if previous.status=='published':
            pack=PACKS.get('custom-'+previous.id)
            if pack: return dict(status='ready',topic=public_pack(pack))
        return dict(id=previous.id,status=previous.status,message='Saved to your curiosity list. New course generation needs an AI connection and content review. You can play the available worlds now.')

    @app.get('/api/v1/learners/{lid}/topic-requests')
    def requests(lid: str, account=Depends(current), session=Depends(db)):
        owned(session,account,lid)
        return [dict(id=r.id,topic=r.topic,status=r.status) for r in session.scalars(select(TopicRequest).where(TopicRequest.learner_id==lid).limit(100))]

    @app.get('/api/v1/learners/{lid}/progress')
    def progress(lid: str, account=Depends(current), session=Depends(db)):
        return summary(session,owned(session,account,lid))

    @app.get('/api/v1/learners/{lid}/worlds/{topic}')
    def world(lid: str, topic: str, account=Depends(current), session=Depends(db)):
        owned(session,account,lid)
        pack = get_pack(topic)
        attempts = list(session.scalars(select(Attempt).where(Attempt.learner_id==lid,Attempt.topic==topic,Attempt.completed.is_(True))))
        done = {a.mode for a in attempts}
        return dict(**public_pack(pack), stages=[dict(mode=m,title=t,done=m in done,locked=m=='boss' and not {'battle','puzzle'}.issubset(done)) for m,t in [('battle','Portal run'),('match','Connection bridge'),('puzzle','Path builder'),('boss','The final guardian'),('timed','Time trial')]])

    @app.post('/api/v1/learners/{lid}/attempts',status_code=201)
    def start(lid: str, body: StartInput, account=Depends(current), session=Depends(db)):
        owned(session,account,lid)
        pack = get_pack(body.topic)
        if body.mode=='boss':
            done=set(session.scalars(select(Attempt.mode).where(Attempt.learner_id==lid,Attempt.topic==body.topic,Attempt.completed.is_(True))))
            if not {'battle','puzzle'}.issubset(done):
                raise HTTPException(409,'Complete Portal run and Path builder first.')
        active=session.scalar(select(Attempt).where(Attempt.learner_id==lid,Attempt.topic==body.topic,Attempt.mode==body.mode,Attempt.completed.is_(False)).order_by(Attempt.started.desc()))
        if active:
            return state(active)
        ids=list(range(len(pack.pairs) if body.mode=='match' else 1 if body.mode=='puzzle' else len(pack.questions)))
        if body.mode in ('battle','timed'):
            mastery=session.scalar(select(Mastery).where(Mastery.learner_id==lid,Mastery.topic==body.topic))
            # Practice weak or unseen items first; boss and placement cover the pack.
            ids.sort(key=lambda i: bool(mastery and mastery.evidence.get(str(i))))
        attempt=Attempt(learner_id=lid,topic=body.topic,mode=body.mode,question_ids=ids,answers=[],hints=[])
        session.add(attempt)
        session.flush()
        return state(attempt)

    def own_attempt(session,account,aid):
        attempt=session.get(Attempt,aid)
        if not attempt:
            raise HTTPException(404,'Round not found.')
        owned(session,account,attempt.learner_id)
        return attempt

    @app.get('/api/v1/attempts/{aid}')
    def resume(aid: str, account=Depends(current),session=Depends(db)):
        return state(own_attempt(session,account,aid))

    @app.post('/api/v1/attempts/{aid}/responses')
    def answer(aid: str,body: AnswerInput,account=Depends(current),session=Depends(db)):
        return respond(session,own_attempt(session,account,aid),body.sequence,body.answer,body.key)

    @app.post('/api/v1/attempts/{aid}/hints')
    def hint(aid: str,account=Depends(current),session=Depends(db)):
        a=own_attempt(session,account,aid)
        if a.completed:
            raise HTTPException(409,'This round is complete.')
        index=len(a.answers)
        a.hints=list(set([*a.hints,index]))
        pack=get_pack(a.topic)
        message='Think about what must happen before the next step.' if a.mode=='puzzle' else 'Connect the idea with what it describes.' if a.mode=='match' else pack.questions[a.question_ids[index]].hint
        return dict(message=message)

    @app.post('/api/v1/learners/{lid}/chat/streams')
    def chat(lid: str,body: ChatInput,account=Depends(current),session=Depends(db)):
        learner=owned(session,account,lid)
        limit('chat:'+lid,10)
        active=session.scalar(select(Attempt).where(Attempt.learner_id==lid,Attempt.completed.is_(False),Attempt.topic==body.topic))
        if active:
            message='You have an active challenge. Use its Hint button for a clue, then finish the round to explore the full lesson.'
        elif privacy_check(body.message):
            message='Please leave personal contact details out of chat. Tell me the idea you want to understand.'
        elif online_ready():
            provider=CompatibleProvider()
            try:
                reply=safe_explain(provider,body.topic,body.message,PACKS[body.topic].lesson if body.topic in PACKS else '')
            except Exception:
                raise HTTPException(502,'An approved reply is unavailable. Try again later or use a guided activity.')
            message=reply.explanation+'\n\n'+reply.follow_up
            session.add(AIUsage(learner_id=lid,operation='tutor',tokens=provider.tokens,model=os.getenv('AI_MODEL','')))
        elif body.topic in PACKS:
            count=session.scalar(select(func.count()).select_from(Attempt).where(Attempt.learner_id==lid,Attempt.topic==body.topic,Attempt.completed.is_(True)))
            message=guided_reply(PACKS[body.topic],body.message,learner.companion,count)
        else:
            message='This topic is on your curiosity list. In guided mode I can teach the published starter worlds. An AI connection is needed for new explanations.'
        session.add(Chat(learner_id=lid,topic=body.topic,response=message))
        # Save before streaming; chunks contain only the approved authored reply.
        session.flush()
        def events():
            yield 'event: status\ndata: '+json.dumps({'mode':'online' if online_ready() else 'guided'})+'\n\n'
            for paragraph in message.split('\n\n'):
                yield 'event: approved_chunk\ndata: '+json.dumps({'text':paragraph+'\n\n'})+'\n\n'
            yield 'event: done\ndata: {}\n\n'
        return StreamingResponse(events(),media_type='text/event-stream')

    @app.get('/api/v1/learners/{lid}/chat')
    def history(lid: str,account=Depends(current),session=Depends(db)):
        owned(session,account,lid)
        return [dict(topic=c.topic,text=c.response) for c in session.scalars(select(Chat).where(Chat.learner_id==lid).order_by(Chat.created.desc()).limit(12))][::-1]

    @app.get('/api/v1/learners/{lid}/shop')
    def shop(lid: str,account=Depends(current),session=Depends(db)):
        learner=owned(session,account,lid)
        inventory=set(session.scalars(select(Inventory.cosmetic).where(Inventory.learner_id==lid)))|{'classic'}
        return [dict(**c,owned=c['id'] in inventory,equipped=c['id']==learner.equipped) for c in COSMETICS]

    @app.post('/api/v1/learners/{lid}/purchases')
    def purchase(lid: str,body: PurchaseInput,account=Depends(current),session=Depends(db)):
        learner=owned(session,account,lid)
        cosmetic=next((c for c in COSMETICS if c['id']==body.cosmetic),None)
        if not cosmetic:
            raise HTTPException(404,'Cosmetic not found.')
        existing=session.scalar(select(Inventory).where(Inventory.learner_id==lid,Inventory.cosmetic==body.cosmetic))
        if not existing and body.cosmetic!='classic':
            coins=session.scalar(select(func.coalesce(func.sum(Reward.coins),0)).where(Reward.learner_id==lid))
            if coins<cosmetic['price']:
                raise HTTPException(409,'Earn a few more coins before unlocking this look.')
            session.add(Inventory(learner_id=lid,cosmetic=body.cosmetic))
            award(session,lid,'purchase:'+body.cosmetic,0,-cosmetic['price'])
        learner.equipped=body.cosmetic
        return dict(equipped=learner.equipped)

    @app.get('/api/v1/learners/{lid}/settings')
    def settings(lid: str,account=Depends(current),session=Depends(db)):
        owned(session,account,lid)
        pref=session.get(Preference,lid)
        return dict(**SettingsInput().model_dump()) if not pref else dict(**pref.settings,leaderboard=pref.leaderboard)

    @app.post('/api/v1/learners/{lid}/settings')
    def save_settings(lid: str,body: SettingsInput,account=Depends(current),session=Depends(db)):
        learner=owned(session,account,lid)
        if learner.age!='18+' and body.leaderboard:
            raise HTTPException(403,'Guardian authorization is required.')
        pref=session.get(Preference,lid)
        if not pref:
            pref=Preference(learner_id=lid)
            session.add(pref)
        pref.leaderboard=body.leaderboard
        pref.settings=body.model_dump(exclude={'leaderboard'})
        return body

    @app.get('/api/v1/learners/{lid}/leaderboard')
    def leaderboard(lid: str,account=Depends(current),session=Depends(db)):
        owned(session,account,lid)
        pref=session.get(Preference,lid)
        if not pref or not pref.leaderboard:
            return []
        # Local adult-only opt-in rankings, generated aliases, no profile links.
        ids=list(session.scalars(select(Preference.learner_id).where(Preference.leaderboard.is_(True))))
        today=india_date()
        scores={i:0 for i in ids}
        for r in session.scalars(select(Reward).where(Reward.learner_id.in_(ids),Reward.xp>0)):
            if india_date(r.created)==today: scores[r.learner_id]+=r.xp
        return [dict(alias='Explorer '+i[:6],points=min(100,score),you=i==lid) for i,score in sorted(scores.items(),key=lambda x:(-min(100,x[1]),x[0]))[:20]]

    @app.post('/api/v1/learners/{lid}/activity')
    def heartbeat(lid: str,account=Depends(current),session=Depends(db)):
        owned(session,account,lid)
        row=session.get(Activity,lid)
        if not row:
            row=Activity(learner_id=lid,seconds=0,last_seen=utcnow());session.add(row)
        elapsed=(utcnow()-row.last_seen).total_seconds()
        if 0<elapsed<=45: row.seconds+=int(elapsed)
        row.last_seen=utcnow()
        return dict(seconds=row.seconds)

    @app.get('/api/v1/learners/{lid}/export')
    def export(lid: str,account=Depends(current),session=Depends(db)):
        learner=owned(session,account,lid)
        return dict(profile=dict(alias=learner.alias,age=learner.age,companion=learner.companion),progress=summary(session,learner),requests=[r.topic for r in session.scalars(select(TopicRequest).where(TopicRequest.learner_id==lid))],companion_messages=[c.response for c in session.scalars(select(Chat).where(Chat.learner_id==lid))])

    @app.delete('/api/v1/learners/{lid}')
    def remove(lid: str,account=Depends(current),session=Depends(db)):
        learner=owned(session,account,lid)
        request_ids=list(session.scalars(select(TopicRequest.id).where(TopicRequest.learner_id==lid)))
        # Published packs remain shared educational content; remove personal request linkage.
        for draft in session.scalars(select(GeneratedPack).where(GeneratedPack.request_id.in_(request_ids))):
            if draft.status=='published':
                draft.request_id=None
            else:
                session.delete(draft)
        session.flush()
        for model in [Attempt,Mastery,Reward,Inventory,TopicRequest,Chat,Activity,Preference,AIUsage]:
            session.execute(delete(model).where(model.learner_id==lid))
        session.execute(delete(Receipt).where(Receipt.key.startswith(lid+':')))
        session.delete(learner)
        return dict(deleted=True)

    @app.get('/api/v1/admin/reviews')
    def reviews(account=Depends(current),session=Depends(db)):
        if account.role!='admin': raise HTTPException(403,'Content reviewer access is required.')
        return [dict(id=d.id,status=d.status,pack=d.payload) for d in session.scalars(select(GeneratedPack).where(GeneratedPack.status=='review_required').limit(50))]

    @app.post('/api/v1/admin/reviews/{draft_id}/{decision}')
    def review(draft_id: str,decision: Literal['publish','reject'],account=Depends(current),session=Depends(db)):
        if account.role!='admin': raise HTTPException(403,'Content reviewer access is required.')
        draft=session.get(GeneratedPack,draft_id)
        if not draft: raise HTTPException(404,'Draft not found.')
        if draft.status!='review_required': raise HTTPException(409,'This draft has already been reviewed.')
        pack=Pack.model_validate(draft.payload)
        draft.status='published' if decision=='publish' else 'rejected'
        draft.reviewer=account.id;draft.reviewed_at=utcnow()
        session.get(TopicRequest,draft.request_id).status=draft.status
        session.flush()
        if decision=='publish': PACKS[pack.id]=pack
        return dict(status=draft.status)

    @app.get('/api/v1/config')
    def config(account=Depends(current)):
        return dict(ai='online' if online_ready() else 'guided')
