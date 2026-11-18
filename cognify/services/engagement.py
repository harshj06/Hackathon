"""Deterministic, idempotent rewards. XP is engagement, never evidence of mastery."""
from datetime import timedelta
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert
from cognify.models import (Reward, Achievement, StudySettings, Review, Mastery,
    Assessment, GameAttempt, LessonCompletion, DocumentAttempt, Concept, Event, now)
from cognify.services.accounts import require_profile
from cognify.adaptive import ENGAGEMENT

BADGES = {
    'first_check': ('First step', 'Complete a diagnostic or verification check.', '◎'),
    'game_explorer': ('Play to learn', 'Complete a learning game.', '✦'),
    'three_day': ('Showing up', 'Learn on three consecutive UTC days.', '☀'),
    'century': ('Momentum', 'Earn 100 XP through learning activities.', '↗'),
    'mastery': ('Concept trophy', 'Meet the mastery threshold for one concept.', '◆'),
    'source_sleuth': ('Source sleuth', 'Complete a document recall check.', '▤'),
    'all_rounder': ('Curious mind', 'Finish games in all three subjects.', '✺'),
}

class StudyInput(BaseModel):
    daily_xp: int = Field(ge=10, le=100)
    weekdays: list[int] = Field(min_length=1, max_length=7)
    minutes: int = Field(ge=5, le=60)
    credential_goal: str = Field(default='', max_length=200)
    roadmap: list[str] = Field(default_factory=list, max_length=6)

    @field_validator('weekdays')
    @classmethod
    def days(cls, value):
        if len(set(value))!=len(value) or any(type(v) is not int or not 0<=v<=6 for v in value):
            raise ValueError('Choose distinct weekdays.')
        return sorted(value)

    @field_validator('roadmap')
    @classmethod
    def steps(cls, value):
        if any(not v.strip() or len(v)>200 for v in value):
            raise ValueError('Each roadmap step needs 1–200 characters.')
        return [v.strip() for v in value]


def study_settings(session, user_id, profile_id):
    profile=require_profile(session,user_id,profile_id)
    row=session.get(StudySettings,profile_id)
    if not row:
        cfg=ENGAGEMENT[profile.age_group]
        # Reading a shared report must not create/write a learner's settings.
        return StudySettings(profile_id=profile_id,daily_xp=cfg['daily_xp'],minutes=cfg['minutes'],
                             weekdays=[0,2,4],credential_goal='',roadmap=[])
    return row


def save_study_settings(session,user_id,profile_id,data:StudyInput):
    require_profile(session,user_id,profile_id,write=True)
    row=session.get(StudySettings,profile_id)
    if not row:
        row=StudySettings(profile_id=profile_id)
        session.add(row)
    from cognify.models import RoadmapProgress
    if row.roadmap!=data.roadmap:
        progress=session.get(RoadmapProgress,profile_id)
        if progress:
            progress.checked=[]
    for name,value in data.model_dump().items():
        setattr(row,name,value)
    return row


def streak_length(dates, today):
    days=set(dates)
    cursor=today if today in days else today-timedelta(days=1)
    count=0
    while cursor in days:
        count+=1;cursor-=timedelta(days=1)
    return count


def snapshot(session,user_id,profile_id,at=None):
    require_profile(session,user_id,profile_id)
    today=(at or now()).date()
    rewards=list(session.scalars(select(Reward).where(Reward.profile_id==profile_id).order_by(Reward.created_at)))
    total=sum(r.xp for r in rewards)
    return dict(total=total,level=1+total//100,level_progress=total%100,
        today=sum(r.xp for r in rewards if r.created_at.date()==today),
        streak=streak_length([r.created_at.date() for r in rewards],today),
        goal=study_settings(session,user_id,profile_id).daily_xp,rewards=rewards,
        badges=list(session.scalars(select(Achievement).where(Achievement.profile_id==profile_id).order_by(Achievement.earned_at.desc()))))


def _award(session,profile_id,source_key,category,xp,at=None):
    """Internal-only: call after a server-validated activity. Atomic unique ledger entry."""
    if type(xp) is not int or not 1<=xp<=50:
        raise ValueError('Invalid reward amount.')
    result=session.execute(insert(Reward).values(profile_id=profile_id,source_key=source_key,
        category=category,xp=xp,created_at=at or now()).on_conflict_do_nothing(index_elements=['profile_id','source_key']))
    return xp if result.rowcount else 0


def refresh_badges(session,user_id,profile_id):
    require_profile(session,user_id,profile_id,write=True)
    session.flush()
    state=snapshot(session,user_id,profile_id)
    checks=session.scalar(select(func.count()).select_from(Assessment).where(Assessment.profile_id==profile_id,Assessment.completed_at.is_not(None)))
    games=list(session.scalars(select(GameAttempt).where(GameAttempt.profile_id==profile_id,GameAttempt.completed_at.is_not(None))))
    mastered=session.scalar(select(Mastery.id).where(Mastery.profile_id==profile_id,Mastery.status=='Mastered').limit(1))
    docs=session.scalar(select(DocumentAttempt.id).where(DocumentAttempt.profile_id==profile_id).limit(1))
    subjects=set(session.scalars(select(Concept.subject).where(Concept.id.in_([g.concept_id for g in games]))))
    conditions={'first_check':bool(checks),'game_explorer':bool(games),'three_day':state['streak']>=3,
        'century':state['total']>=100,'mastery':bool(mastered),'source_sleuth':bool(docs),'all_rounder':len(subjects)>=3}
    for badge,earned in conditions.items():
        if earned:
            session.execute(insert(Achievement).values(profile_id=profile_id,badge=badge,earned_at=now())
                .on_conflict_do_nothing(index_elements=['profile_id','badge']))


def reward_assessment(session,user_id,attempt):
    require_profile(session,user_id,attempt.profile_id,write=True)
    if attempt.completed_at is None or attempt.score is None:
        raise ValueError('Only completed assessments earn XP.')
    from cognify.models import Question
    concept_ids=list(session.scalars(select(Question.concept_id).where(Question.id.in_(attempt.question_ids)).distinct()))
    key=f'assessment:{attempt.kind}:{",".join(sorted(concept_ids))}:{attempt.completed_at.date()}'
    xp=_award(session,attempt.profile_id,key,'Assessment',10+round(attempt.score*20),at=attempt.completed_at)
    for cid in concept_ids:
        mastery=session.scalar(select(Mastery).where(Mastery.profile_id==attempt.profile_id,Mastery.concept_id==cid))
        profile=require_profile(session,user_id,attempt.profile_id)
        interval=ENGAGEMENT[profile.age_group]['review_days']
        row=session.scalar(select(Review).where(Review.profile_id==attempt.profile_id,Review.concept_id==cid))
        if mastery and mastery.status=='Mastered':
            interval=min(30,max(7,(row.interval_days*2 if row else 7)))
        elif mastery and mastery.score>=.5:
            interval=max(2,interval)
        if not row:
            row=Review(profile_id=attempt.profile_id,concept_id=cid,due_at=now(),interval_days=interval)
            session.add(row)
        row.interval_days=interval
        row.due_at=attempt.completed_at+timedelta(days=interval)
    refresh_badges(session,user_id,attempt.profile_id)
    return xp


def complete_lesson(session,user_id,profile_id,concept_id):
    require_profile(session,user_id,profile_id,write=True)
    if not session.get(Concept,concept_id):
        raise ValueError('Unknown concept.')
    session.execute(insert(LessonCompletion).values(profile_id=profile_id,concept_id=concept_id,completed_at=now())
        .on_conflict_do_nothing(index_elements=['profile_id','concept_id']))
    xp=_award(session,profile_id,f'lesson:{concept_id}','Lesson',5)
    if xp:
        session.add(Event(profile_id=profile_id,kind='Lesson complete',detail='Completed a guided concept lesson.'))
    refresh_badges(session,user_id,profile_id)
    return xp


def due_reviews(session,user_id,profile_id,at=None):
    require_profile(session,user_id,profile_id)
    return list(session.scalars(select(Review).where(Review.profile_id==profile_id,Review.due_at<= (at or now())).order_by(Review.due_at)))


def study_dates(settings,start=None):
    start=(start or now()).date()
    return [start+timedelta(days=i) for i in range(14) if (start+timedelta(days=i)).weekday() in settings.weekdays]


def mark_milestone(session,user_id,profile_id,index,checked):
    from cognify.models import RoadmapProgress
    require_profile(session,user_id,profile_id,write=True)
    plan=study_settings(session,user_id,profile_id)
    if type(index) is not int or not 0<=index<len(plan.roadmap) or type(checked) is not bool:
        raise ValueError('Choose an existing milestone.')
    row=session.get(RoadmapProgress,profile_id)
    if not row:
        row=RoadmapProgress(profile_id=profile_id,checked=[]);session.add(row)
    row.checked=sorted(set(row.checked+[index])) if checked else [i for i in row.checked if i!=index]
    return row
