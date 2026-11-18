from datetime import datetime,timedelta
import pytest
from sqlalchemy import select,func
from cognify.models import Reward,Mastery,Review,Achievement,GameAttempt,Question,SchemaVersion,Profile
from cognify.services.engagement import snapshot,streak_length,complete_lesson,StudyInput,save_study_settings,study_settings,study_dates,due_reviews
from cognify.services.games import start_game,submit_game,get_game,unlocked,CONTENT,MODES
from cognify.services.learning import start_assessment,submit_assessment
from cognify.services.accounts import register,AccessDenied

@pytest.mark.parametrize('cid',list(CONTENT))
@pytest.mark.parametrize('mode',list(MODES))
def test_every_game_has_deterministic_keys_and_does_not_grade_mastery(factory,learner,cid,mode):
    u,p=learner
    with factory.begin() as s:
        # All advanced scenarios can be unlocked by prerequisite game evidence.
        for prerequisite in ['addition','observation','sequence']:
            if prerequisite!=cid:
                a=start_game(s,u.id,p.id,prerequisite,'match')
                submit_game(s,u.id,a.id,a.payload['correct'])
        a=start_game(s,u.id,p.id,cid,mode)
        submit_game(s,u.id,a.id,a.payload['correct'])
        assert a.score==1 and a.xp==25 and a.completed_at is not None
        assert s.scalar(select(func.count()).select_from(Mastery))==0
        assert 'game_explorer' in [b.badge for b in snapshot(s,u.id,p.id)['badges']]


def test_repeat_game_xp_is_idempotent_and_bad_answers_do_not_commit(factory,learner):
    u,p=learner
    with factory.begin() as s:
        a=start_game(s,u.id,p.id,'addition','match')
        with pytest.raises(ValueError):
            submit_game(s,u.id,a.id,[None]*3)
        assert a.completed_at is None
        with pytest.raises(ValueError):
            submit_game(s,u.id,a.id,[0,0,0])
        submit_game(s,u.id,a.id,a.payload['correct'])
        with pytest.raises(ValueError,match='already'):
            submit_game(s,u.id,a.id,a.payload['correct'])
        b=start_game(s,u.id,p.id,'addition','match')
        submit_game(s,u.id,b.id,b.payload['correct'])
        assert b.xp==0
        assert snapshot(s,u.id,p.id)['total']==25


def test_unlock_and_cross_account_boundaries(factory,learner):
    u,p=learner
    with factory.begin() as s:
        outsider=register(s,'outsider','a-long-password','learner')
        assert not unlocked(s,u.id,p.id,'fractions')
        with pytest.raises(ValueError,match='prerequisite'):
            start_game(s,u.id,p.id,'fractions','scenario')
        a=start_game(s,u.id,p.id,'addition','order')
        with pytest.raises(AccessDenied):
            get_game(s,outsider.id,a.id)
        with pytest.raises(AccessDenied):
            complete_lesson(s,outsider.id,p.id,'addition')
        submit_game(s,u.id,a.id,a.payload['correct'])
        assert unlocked(s,u.id,p.id,'fractions')


def test_lessons_award_once_and_study_plan_survives_sessions(factory,learner):
    u,p=learner
    with factory.begin() as s:
        assert complete_lesson(s,u.id,p.id,'addition')==5
        assert complete_lesson(s,u.id,p.id,'addition')==0
        data=StudyInput(daily_xp=40,weekdays=[1,3],minutes=20,credential_goal='My course',roadmap=['Map skills','Review gaps'])
        save_study_settings(s,u.id,p.id,data)
    with factory() as s:
        plan=study_settings(s,u.id,p.id)
        assert plan.daily_xp==40 and plan.roadmap==['Map skills','Review gaps']
        assert len(study_dates(plan,datetime(2026,11,18)))==4


def test_streak_midnight_and_breaks():
    today=datetime(2026,11,18).date()
    assert streak_length([today,today-timedelta(days=1),today-timedelta(days=2)],today)==3
    assert streak_length([today-timedelta(days=1)],today)==1
    assert streak_length([today-timedelta(days=2)],today)==0
    assert streak_length([today,today],today)==1


def test_assessments_issue_rewards_and_schedule_review(factory,learner):
    u,p=learner
    with factory.begin() as s:
        a=start_assessment(s,u.id,p.id,'addition')
        submit_assessment(s,u.id,a.id,{qid:s.get(Question,qid).correct for qid in a.question_ids})
        assert snapshot(s,u.id,p.id)['total']==30
        r=s.scalar(select(Review).where(Review.profile_id==p.id))
        assert r.interval_days==2 and not due_reviews(s,u.id,p.id)
        assert due_reviews(s,u.id,p.id,at=r.due_at+timedelta(seconds=1))
        b=start_assessment(s,u.id,p.id,'addition','verification')
        submit_assessment(s,u.id,b.id,{qid:s.get(Question,qid).correct for qid in b.question_ids})
        assert r.interval_days==7
        assert 'mastery' in [b.badge for b in snapshot(s,u.id,p.id)['badges']]


def test_study_input_rejects_out_of_bounds():
    for values in [dict(daily_xp=1000,weekdays=[0],minutes=10),dict(daily_xp=30,weekdays=[9],minutes=10),dict(daily_xp=30,weekdays=[],minutes=10)]:
        with pytest.raises(ValueError):
            StudyInput(**values)


def test_additive_schema_upgrade_preserves_existing_records(tmp_path):
    from cognify.db import make_engine,initialize,session_factory
    from cognify.models import User
    from sqlalchemy import text
    engine=make_engine('sqlite:///'+str(tmp_path/'old.db'))
    # Actual v1 table compatible with the new app; startup adds tables, not replacements.
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(40) UNIQUE NOT NULL, password_hash TEXT NOT NULL, role VARCHAR(20) NOT NULL, demo BOOLEAN NOT NULL, created_at DATETIME NOT NULL)'))
        conn.execute(text("INSERT INTO users VALUES (7,'preserved','hash','parent',0,'2026-11-17 12:00:00')"))
    initialize(engine);initialize(engine)
    with session_factory(engine)() as s:
        assert s.get(User,7).username=='preserved'
        assert s.get(SchemaVersion,2)
    engine.dispose()


def test_roadmap_checks_reset_when_milestones_change(factory,learner):
    from cognify.services.engagement import mark_milestone
    from cognify.models import RoadmapProgress
    u,p=learner
    with factory.begin() as s:
        data=StudyInput(daily_xp=30,weekdays=[0],minutes=15,roadmap=['Prepare','Practise'])
        save_study_settings(s,u.id,p.id,data)
        mark_milestone(s,u.id,p.id,0,True)
        assert s.get(RoadmapProgress,p.id).checked==[0]
        save_study_settings(s,u.id,p.id,data.model_copy(update={'roadmap':['Read','Check']}))
        assert s.get(RoadmapProgress,p.id).checked==[]


def test_due_reviews_are_private(factory,learner):
    u,p=learner
    with factory.begin() as s:
        stranger=register(s,'private_review','long-password','learner')
        with pytest.raises(AccessDenied):
            due_reviews(s,stranger.id,p.id)
