"""Short, interactive learner journeys; every displayed reward is persisted."""
import html
import json
from pathlib import Path
import streamlit.components.v1 as components
from datetime import timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import select
from cognify.models import Concept,Mastery,LessonCompletion,GameAttempt,Review,Assessment,Answer,Question
from cognify.adaptive import ENGAGEMENT,EXPERIENCES,CAREER_PATHS
from cognify.services.accounts import require_profile,ProfileInput,update_profile
from cognify.services.learning import build_path,report
from cognify.services.engagement import (snapshot,study_settings,save_study_settings,StudyInput,
    BADGES,due_reviews,complete_lesson,study_dates)
from cognify.services.games import MODES,unlocked,start_game,get_game,submit_game
from cognify.services.conversation import conversation,send_message
from cognify.ui.style import hero,card,mascot
from cognify.ui.routing import go

SUBJECT_ICONS={'Mathematics':'◒','Science':'✺','Computing':'⌘'}


def concept_picker(factory,profile,key):
    with factory() as session:
        concepts=list(session.scalars(select(Concept).where(Concept.subject.in_(profile.subjects)).order_by(Concept.subject,Concept.id)))
    ids=[c.id for c in concepts]
    focused=st.session_state.get('focus_concept')
    cid=st.selectbox('Choose a concept',ids,index=ids.index(focused) if focused in ids else 0,
        format_func=lambda cid:next(c.title for c in concepts if c.id==cid),key=key)
    return next(c for c in concepts if c.id==cid)


def reward_strip(state):
    columns=st.columns(4)
    for col,label,value in zip(columns,['Total XP','Level','Learning streak','Today'],
            [str(state['total']),str(state['level']),f'{state["streak"]} '+('day' if state['streak']==1 else 'days'),f'{state["today"]} / {state["goal"]} XP']):
        with col:
            st.markdown(f'<div class="stat"><span>{label}</span><strong>{value}</strong></div>',unsafe_allow_html=True)
    st.progress(min(1.,state['today']/state['goal']),text='Daily goal complete ✦' if state['today']>=state['goal'] else 'A little learning, every day · UTC')


def dashboard(factory,user,profile):
    cfg=ENGAGEMENT[profile.age_group]
    with factory.begin() as session:
        state=snapshot(session,user.id,profile.id)
        path=build_path(session,user.id,profile.id)
        rows=report(session,user.id,profile.id)
        reviews=due_reviews(session,user.id,profile.id)
        concepts={c.id:c for c in session.scalars(select(Concept))}
    hero(f'Your next “I get it”, {profile.nickname}.', 'One small mission. A new way to see it.',cfg['mission'])
    reward_strip(state)
    left,right=st.columns([1.75,1])
    with left:
        st.subheader('Your next steps')
        next_id=reviews[0].concept_id if reviews else (path[0] if path else next(iter(concepts)))
        with st.container(border=True):
            st.caption('↻ READY TO REVISIT' if reviews else '✦ YOUR NEXT MISSION')
            st.subheader(concepts[next_id].title)
            st.caption(f'{concepts[next_id].subject} · {cfg["minutes"]} minutes · Learn → Play → Verify')
            st.button('Continue my mission',type='primary',use_container_width=True,on_click=go,args=('Learn',next_id))
        cols=st.columns(2)
        with cols[0]:
            card('Play with an idea','Match pairs. Reorder steps. Solve a scenario.','GAME LAB')
            st.button('Find a game',use_container_width=True,on_click=go,args=('Games',))
        with cols[1]:
            card('Ask a better question','Buddy can unpack an idea with you.','YOUR LEARNING PARTNER')
            st.button('Talk to Buddy',use_container_width=True,on_click=go,args=('Buddy Chat',next_id))
    with right:
        mascot()
        st.markdown('**Your learning trail**')
        for i,cid in enumerate(path[:cfg['steps']+1]):
            st.markdown(f'<div class="trail"><span>{i+1}</span>{html.escape(concepts[cid].title)}</div>',unsafe_allow_html=True)
        if not path:
            st.success('Starter trail complete. Revisit a concept to keep it fresh.')
        st.caption(f'{sum(r["status"]=="Mastered" for r in rows)} concepts mastered · {len(reviews)} reviews due')
    if state['badges']:
        st.subheader('Your latest wins')
        for col,badge in zip(st.columns(min(3,len(state['badges']))),state['badges'][:3]):
            title,description,icon=BADGES[badge.badge]
            with col:
                card(title,description,icon+' EARNED')
    if profile.age_group in ['18–24','25+']:
        st.button('Plan study & career milestones',on_click=go,args=('Study plan',))


def interactive_model(concept):
    if concept.id=='addition':
        a,b=st.columns(2)
        first=a.slider('First group',1,10,3)
        second=b.slider('Second group',1,10,2)
        st.markdown(f'<div class="playground"><div class="dots">{"● "*first}<span> + </span>{"● "*second}</div><strong>{first} + {second} = {first+second}</strong></div>',unsafe_allow_html=True)
    elif concept.id=='fractions':
        total=st.slider('Equal parts in the whole',2,12,4)
        selected=st.slider('Selected parts',0,total,min(3,total))
        boxes=''.join(f'<span class="fraction-part {"filled" if i<selected else ""}"></span>' for i in range(total))
        st.markdown(f'<div class="playground"><div class="fraction-grid">{boxes}</div><strong>{selected}/{total}</strong></div>',unsafe_allow_html=True)
        st.caption('The parts stay equal. The numerator counts selected parts.')
    elif concept.id=='loops':
        repeats=st.slider('Number of repetitions',1,8,4)
        dots=st.slider('Dots per repetition',1,4,2)
        st.code('\n'.join(f'Round {i+1}: '+ '● '*dots for i in range(repeats)),language=None)
        st.success(f'{repeats} × {dots} = {repeats*dots} dots')
    elif concept.id=='sequence':
        steps=['Open editor','Write text','Save file']
        first=st.selectbox('Which step goes first?',steps,index=None)
        if first:
            (st.success if first==steps[0] else st.info)('Yes. Open the editor, write, then save.' if first==steps[0] else 'Think about what must exist before you can write in it.')
    elif concept.id=='observation':
        claim=st.radio('“The plant grew because it likes music.”',['Observation','Explanation to test'],index=None,horizontal=True)
        if claim:
            (st.success if claim=='Explanation to test' else st.info)('That is a proposed reason. A measured height would be an observation.')
    else:
        changed=st.multiselect('Testing light and plant growth: what will you change?',['Light','Water amount','Plant type'],default=['Light'])
        if changed==['Light']:
            st.success('One changed factor. Keep water and plant type alike, then measure growth.')
        else:
            st.info('Change only light in this comparison. Several changes make the cause unclear.')
    st.caption('Explore freely. This interactive example is unscored.')


def learn(factory,settings,user,profile):
    from cognify.ui.views import show_lesson
    hero('Make it click.', 'Explore an idea. Try it. Take it into a game.','LEARNING STUDIO')
    concept=concept_picker(factory,profile,'learn_concept')
    with factory() as session:
        learned=session.scalar(select(LessonCompletion.id).where(LessonCompletion.profile_id==profile.id,LessonCompletion.concept_id==concept.id))
    stage=st.radio('Your mission',['1 · Explore','2 · Connect','3 · Try & verify'],horizontal=True,key=f'lesson_stage_{profile.id}_{concept.id}')
    st.progress((['1 · Explore','2 · Connect','3 · Try & verify'].index(stage)+1)/3)
    if stage.startswith('1'):
        st.subheader(concept.title)
        st.write(concept.lesson['explanation'].split('. ')[0]+'.')
        interactive_model(concept)
    elif stage.startswith('2'):
        st.subheader('A familiar example')
        st.write(concept.lesson['example'])
        if st.button('Flip the idea card'):
            st.info(concept.lesson['visual'])
        with st.expander('Ask for a personalized explanation'):
            show_lesson(factory,settings,user,profile,concept)
    else:
        st.subheader('Put the idea to work')
        st.write(concept.lesson['activity'])
        if not learned:
            if st.button('I tried the activity · finish lesson',type='primary'):
                with factory.begin() as session:
                    xp=complete_lesson(session,user.id,profile.id,concept.id)
                st.success(f'Lesson complete. +{xp} XP for taking part. Now check your understanding.')
        else:
            st.success('Lesson completed ✦ Your next challenge is ready.')
        cols=st.columns(2)
        cols[0].button('Play this concept',use_container_width=True,on_click=go,args=('Games',concept.id))
        cols[1].button('Verify understanding',use_container_width=True,on_click=go,args=('Practice',concept.id))
    st.caption('Lesson XP celebrates participation. Assessment answers determine mastery.')


def game_submit_callback(factory,user_id,attempt_id,count):
    try:
        responses=[st.session_state[f'game_answer_{attempt_id}_{i}'] for i in range(count)]
        with factory.begin() as session:
            attempt=submit_game(session,user_id,attempt_id,responses)
        st.session_state.game_celebration=attempt.id
    except ValueError as exc:
        st.session_state.game_error=str(exc)


def games(factory,user,profile):
    hero('Pick a way to play.', 'Match, order, or solve a mini-scenario. Every round is practice with a little sparkle.','GAME ARCADE')
    with factory() as session:
        reward_state = snapshot(session, user.id, profile.id)
    st.markdown(f'''<div class="quest-banner">
        <div><span class="quest-kicker">GAME ARCADE</span><strong>Choose your challenge</strong>
        <p>Replay any round. XP is a bonus; the real win is making the connection.</p></div>
        <div class="quest-reward"><span>✦</span><b>{reward_state["total"]} XP</b><small>your total so far</small></div>
    </div>''', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Pick a concept</div>', unsafe_allow_html=True)
    concept=concept_picker(factory,profile,'game_concept')
    with factory() as session:
        available=unlocked(session,user.id,profile.id,concept.id)
    cols=st.columns(3)
    details={'match':('Match the pairs','Connect ideas with their meanings.','↔'),
             'order':('Put it in order','Build a sequence that works.','≡'),
             'scenario':('Scenario quest','Use the idea in a real situation.','◇')}
    for col,(mode,(title,description,icon)) in zip(cols,details.items()):
        with col:
            st.markdown(f'<div class="game-card"><span class="quest-icon">{icon}</span><h3>{title}</h3><p>{description}</p></div>', unsafe_allow_html=True)
            locked=mode=='scenario' and not available
            if st.button('Unlock with prerequisites' if locked else f'Play {title.lower()}',disabled=locked,key=f'start_{mode}',use_container_width=True):
                with factory.begin() as session:
                    attempt=start_game(session,user.id,profile.id,concept.id,mode)
                st.session_state.game_id=attempt.id
            if locked:
                st.caption('Complete a prerequisite game at 80%, or reach 50% in its assessment.')
    aid=st.session_state.get('game_id')
    if not aid:
        st.caption('Up to 25 XP per concept and game mode each UTC day. Replay freely for practice.')
        return
    with factory() as session:
        attempt=get_game(session,user.id,aid)
    if attempt.profile_id!=profile.id or attempt.concept_id!=concept.id:
        return
    st.divider()
    st.subheader(MODES[attempt.mode])
    if attempt.completed_at:
        correct=sum(a==b for a,b in zip(attempt.responses,attempt.payload['correct']))
        st.success(f'{correct}/{len(attempt.responses)} connections found · +{attempt.xp} XP')
        if attempt.xp==0:
            st.caption('You already earned this activity’s XP today. This round still counts as practice.')
        if st.session_state.pop('game_celebration',None)==attempt.id and not st.session_state.get('reduce_motion'):
            st.balloons()
        for prompt,choice,right in zip(attempt.payload['prompts'],attempt.responses,attempt.payload['correct']):
            st.write(('✓ ' if choice==right else '↻ ')+prompt+' → '+attempt.payload['options'][right])
        st.info(attempt.payload['explanation'])
        st.button('Check what stuck',on_click=go,args=('Practice',concept.id),type='primary')
        return
    game_data = dict(attempt.payload, mode=attempt.mode, reduced=st.session_state.get('reduce_motion', False))
    source = Path(__file__).with_name('arcade.html').read_text()
    # Escape HTML delimiters before embedding curricular strings in a script.
    encoded = json.dumps(game_data).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    components.html(source.replace('__GAME_DATA__', encoded), height=790, scrolling=True)
    st.caption('Arcade stars are for this play session. Save a check below to earn profile XP.')
    with st.expander('Save what you learned · earn XP'):
        with st.form(f'game_{aid}'):
            st.caption('Use each answer once.' if attempt.mode!='scenario' else 'Choose the best next step.')
            for i,prompt in enumerate(attempt.payload['prompts']):
                st.selectbox(prompt,list(range(len(attempt.payload['options']))),index=None,
                    format_func=lambda i:attempt.payload['options'][i],key=f'game_answer_{aid}_{i}')
            st.form_submit_button('Check my connections',type='primary',on_click=game_submit_callback,args=(factory,user.id,aid,len(attempt.payload['prompts'])))
    if st.session_state.get('game_error'):
        st.error(st.session_state.pop('game_error'))


def chat(factory,settings,user,profile):
    from cognify.ui.views import narration
    hero('A question is a great start.', 'Explore one concept with Buddy. Keep personal details out of your messages.','BUDDY CHAT')
    concept=concept_picker(factory,profile,'chat_concept')
    st.caption('Offline guided tutor' if user.demo or not settings.api_key or not profile.ai_enabled else 'Online AI tutor · replies can make mistakes')
    with factory() as session:
        messages=conversation(session,user.id,profile.id,concept.id)
    for message in messages:
        with st.chat_message(message.role,avatar='🤖' if message.role=='assistant' else None):
            st.text(message.text)
            if message.source:
                st.caption(message.source)
    if not messages:
        with st.chat_message('assistant',avatar='🤖'):
            st.write(f'Let’s explore {concept.title.lower()}. Try one of these questions.')
    prompt=None
    cols=st.columns(3)
    for col,label in zip(cols,['Show me an example','Help me picture it','Give me an activity']):
        if col.button(label,use_container_width=True):
            prompt=label
    typed=st.chat_input('What would you like to understand?',max_chars=1000)
    if prompt or typed:
        with st.spinner('Buddy is thinking…'):
            send_message(factory,settings,user.id,profile.id,concept.id,prompt or typed)
        st.rerun()
    if messages and messages[-1].role=='assistant':
        with st.expander('Listen to Buddy'):
            narration(settings,user,profile,messages[-1].text)
    st.button('Turn this into a challenge',on_click=go,args=('Games',concept.id))


def achievements(factory,user,profile):
    hero('Look what you’re building.', 'Every badge has a real learning activity behind it.','YOUR COLLECTION')
    with factory() as session:
        state=snapshot(session,user.id,profile.id)
    reward_strip(state)
    earned={b.badge:b for b in state['badges']}
    cols=st.columns(3)
    for i,(key,(title,description,icon)) in enumerate(BADGES.items()):
        with cols[i%3]:
            card(title,description,icon+(' EARNED' if key in earned else ' TO DISCOVER'))
            if key in earned:
                st.caption(earned[key].earned_at.strftime('Earned %d %b %Y · UTC'))
    st.caption('Badges remain earned when a streak ends or a concept needs another review. Taking a break never removes XP.')
    if state['rewards']:
        df=pd.DataFrame([{'Date':r.created_at.date(),'XP':r.xp,'Activity':r.category} for r in state['rewards']])
        daily=df.groupby('Date',as_index=False).XP.sum()
        daily['Total XP']=daily.XP.cumsum()
        st.plotly_chart(px.area(daily,x='Date',y='Total XP',template='plotly_white',color_discrete_sequence=['#6554C0']),use_container_width=True)
        with st.expander('Your XP ledger'):
            st.dataframe(df,hide_index=True,use_container_width=True)
    else:
        st.button('Earn your first discovery',on_click=go,args=('Learn',))


def save_plan_callback(factory,user_id,profile_id):
    try:
        prefix=f'study_{profile_id}_'
        data=StudyInput(daily_xp=st.session_state[prefix+'xp'],minutes=st.session_state[prefix+'minutes'],
            weekdays=st.session_state[prefix+'days'],credential_goal=st.session_state[prefix+'goal'],
            roadmap=[line.strip() for line in st.session_state[prefix+'steps'].splitlines() if line.strip()])
        with factory.begin() as session:
            save_study_settings(session,user_id,profile_id,data)
        st.session_state.flash='Study plan saved.'
    except ValueError as exc:
        st.session_state.plan_error=str(exc)


def study_plan(factory,user,profile):
    hero('Make room for your next skill.', 'A realistic rhythm, a clear goal, and one next step.','STUDY PLAN')
    with factory() as session:
        plan=study_settings(session,user.id,profile.id)
        reviews=due_reviews(session,user.id,profile.id)
        concepts={c.id:c for c in session.scalars(select(Concept))}
    st.write('**Your goal:** '+profile.goals)
    if profile.age_group in ['18–24','25+']:
        track=st.selectbox('Applied skill path',list(CAREER_PATHS))
        subject,outcome=CAREER_PATHS[track]
        st.caption(outcome)
        if st.button('Use this skill path'):
            data=ProfileInput(**{name:getattr(profile,name) for name in ProfileInput.model_fields})
            data.subjects=[subject];data.goals=outcome
            with factory.begin() as session:
                update_profile(session,user.id,profile.id,data);build_path(session,user.id,profile.id)
            st.session_state.flash='Skill path updated.'
            st.rerun()
    prefix=f'study_{profile.id}_'
    with st.form('study_plan'):
        a,b=st.columns(2)
        a.slider('Daily XP goal',10,100,plan.daily_xp,step=10,key=prefix+'xp')
        b.slider('Minutes per study session',5,60,plan.minutes,step=5,key=prefix+'minutes')
        st.multiselect('Study days',list(range(7)),default=plan.weekdays,
            format_func=lambda i:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i],key=prefix+'days')
        st.text_input('Personal course or certification goal (optional)',value=plan.credential_goal,max_chars=200,key=prefix+'goal')
        st.text_area('Your preparation milestones — one per line',value='\n'.join(plan.roadmap),max_chars=1200,key=prefix+'steps',
            placeholder='Identify the official syllabus\nMap prerequisite skills\nPractise representative tasks\nReview gaps before booking an exam')
        st.caption('This is your planning checklist, not a certificate or a claim that the starter curriculum covers an external exam. No notifications are scheduled.')
        st.form_submit_button('Save study plan',type='primary',on_click=save_plan_callback,args=(factory,user.id,profile.id))
    if st.session_state.get('plan_error'):
        st.error(st.session_state.pop('plan_error'))
    if plan.roadmap:
        from cognify.models import RoadmapProgress
        from cognify.services.engagement import mark_milestone
        with factory() as session:
            progress=session.get(RoadmapProgress,profile.id)
            checked=progress.checked if progress else []
        st.subheader('Preparation milestones')
        st.progress(len(checked)/len(plan.roadmap))
        for i,title in enumerate(plan.roadmap):
            value=st.checkbox(title,value=i in checked,key=f'milestone_{profile.id}_{i}_{title}')
            if value!=(i in checked):
                with factory.begin() as session:
                    mark_milestone(session,user.id,profile.id,i,value)
                st.rerun()
    st.subheader('Your next two weeks')
    schedule=study_dates(plan)
    st.dataframe(pd.DataFrame([{'Session':date.strftime('%a %d %b'),'Minutes':plan.minutes,'Focus':'Review due concepts, then continue your trail'} for date in schedule]),hide_index=True,use_container_width=True)
    if reviews:
        st.subheader('Ready for another look')
        for review in reviews:
            st.button(f'Revisit {concepts[review.concept_id].title}',key=f'review_{review.id}',on_click=go,args=('Practice',review.concept_id))
    else:
        st.caption('Complete an assessment to schedule your first concept review. Intervals adapt to your evidence.')


def improvement(factory,user,profile):
    """Comparable repeat-question change, clearly separated from broad efficacy claims."""
    with factory() as session:
        require_profile(session,user.id,profile.id)
        records=session.execute(select(Answer,Question).join(Question,Answer.question_id==Question.id)
            .join(Assessment,Assessment.id==Answer.assessment_id).where(Assessment.profile_id==profile.id)
            .order_by(Assessment.completed_at,Answer.id)).all()
    grouped={}
    for answer,question in records:
        grouped.setdefault(question.id,[]).append((answer.correct,question.concept_id))
    changes={}
    for values in grouped.values():
        if len(values)>1:
            changes.setdefault(values[0][1],[]).append((int(values[-1][0])-int(values[0][0]))*100)
    if changes:
        st.subheader('What changed on repeated questions')
        st.dataframe(pd.DataFrame([{'Concept':cid,'Repeated questions':len(values),'First → latest change (percentage points)':round(sum(values)/len(values),1)} for cid,values in changes.items()]),hide_index=True,use_container_width=True)
        st.caption('Same question IDs only. Familiarity can affect results; this is not a causal measure of learning effectiveness.')
