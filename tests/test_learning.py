import pytest
from sqlalchemy import select, func
from cognify.models import Question, Answer, Assessment, Mastery, LearningPath
from cognify.services.learning import start_assessment, submit_assessment, mastery_rows, ordered_concepts, build_path


def test_catalog_has_unique_options_and_valid_keys(factory):
    with factory() as s:
        qs=list(s.scalars(select(Question)))
        assert len(qs)==72
        for q in qs:
            assert len(set(q.options))==4, q.id
            assert 0<=q.correct<4
            assert str(q.correct) not in q.misconceptions
            assert len(q.misconceptions)==3


def take(factory,u,p,concept,kind='diagnostic',correct=True):
    with factory.begin() as s:
        a=start_assessment(s,u.id,p.id,concept,kind)
        choices={qid:s.get(Question,qid).correct if correct else (s.get(Question,qid).correct+1)%4 for qid in a.question_ids}
        submit_assessment(s,u.id,a.id,choices)
    return a


def test_deterministic_mastery_and_verification(factory,learner):
    u,p=learner
    a=take(factory,u,p,'fractions')
    assert a.score==1
    with factory() as s:
        rows=mastery_rows(s,u.id,p.id)
        assert len(rows)==2
        assert all(r.status=='Developing' and r.evidence==3 for r in rows)
    take(factory,u,p,'fractions','verification')
    with factory() as s:
        rows=mastery_rows(s,u.id,p.id)
        assert all(r.status=='Mastered' and r.evidence==6 for r in rows)
        path=s.get(LearningPath,p.id).concept_ids
        assert 'addition' not in path and 'fractions' not in path


def test_wrong_answers_record_possible_gaps(factory,learner):
    u,p=learner
    a=take(factory,u,p,'loops',correct=False)
    assert a.score==0
    with factory() as s:
        assert all(r.status=='Needs practice' for r in mastery_rows(s,u.id,p.id))
        assert all(a.misconception for a in s.scalars(select(Answer)))
        assert s.get(LearningPath,p.id).concept_ids.index('sequence') < s.get(LearningPath,p.id).concept_ids.index('loops')


def test_repetition_does_not_inflate_evidence(factory,learner):
    u,p=learner
    for _ in range(4):
        take(factory,u,p,'addition',correct=False)
    with factory() as s:
        assert mastery_rows(s,u.id,p.id)[0].evidence==3


def test_incomplete_and_invalid_answers_are_atomic(factory,learner):
    u,p=learner
    with factory.begin() as s:
        a=start_assessment(s,u.id,p.id,'addition')
    for choices in [{}, {qid:99 for qid in a.question_ids}, {qid:None for qid in a.question_ids}]:
        with pytest.raises(ValueError),factory.begin() as s:
            submit_assessment(s,u.id,a.id,choices)
        with factory() as s:
            assert s.get(Assessment,a.id).completed_at is None
            assert s.scalar(select(func.count()).select_from(Answer))==0


def test_double_submit_is_rejected(factory,learner):
    u,p=learner
    a=take(factory,u,p,'addition')
    with pytest.raises(ValueError,match='already'),factory.begin() as s:
        submit_assessment(s,u.id,a.id,{})
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(Answer))==3


def test_difficulty_uses_performance_not_age(factory,learner):
    u,p=learner
    take(factory,u,p,'addition')
    with factory.begin() as s:
        a=start_assessment(s,u.id,p.id,'addition','verification')
        assert all(s.get(Question,qid).difficulty==2 for qid in a.question_ids)


def test_path_rejects_unknown_concept(factory):
    with factory() as s,pytest.raises(ValueError,match='Unknown'):
        ordered_concepts(s,['unknown'])


def test_age_changes_format_but_keeps_correct_key(factory):
    from cognify.adaptive import display_choices
    with factory() as s:
        for q in s.scalars(select(Question)):
            for age,count in [('5–8',2),('9–12',3),('13–17',4),('18–24',4),('25+',4)]:
                shown=display_choices(q,age)
                assert len(shown)==count and q.correct in shown
