from collections import defaultdict
from sqlalchemy import select, update
from cognify.models import Concept, Question, Assessment, Answer, Mastery, LearningPath, Event, now
from cognify.services.accounts import require_profile


def ordered_concepts(session, targets):
    ordered, visiting = [], set()
    def visit(cid):
        if cid in ordered:
            return
        if cid in visiting:
            raise ValueError('Curriculum prerequisite cycle detected.')
        concept = session.get(Concept, cid)
        if not concept:
            raise ValueError('Unknown concept.')
        visiting.add(cid)
        for prerequisite in concept.prerequisites:
            visit(prerequisite)
        visiting.remove(cid)
        ordered.append(cid)
    for target in targets:
        visit(target)
    return ordered


def mastery_rows(session, user_id, profile_id):
    require_profile(session, user_id, profile_id)
    return list(session.scalars(select(Mastery).where(Mastery.profile_id == profile_id)))


def build_path(session, user_id, profile_id):
    profile = require_profile(session, user_id, profile_id, write=True)
    targets = list(session.scalars(select(Concept.id).where(Concept.subject.in_(profile.subjects)).order_by(Concept.id)))
    mastered = {m.concept_id for m in mastery_rows(session, user_id, profile_id) if m.status == 'Mastered'}
    sequence = [cid for cid in ordered_concepts(session, targets) if cid not in mastered]
    path = session.get(LearningPath, profile_id)
    if not path:
        path = LearningPath(profile_id=profile_id, concept_ids=sequence)
        session.add(path)
    else:
        path.concept_ids, path.updated_at = sequence, now()
    return sequence


def start_assessment(session, user_id, profile_id, concept_id, kind='diagnostic'):
    require_profile(session, user_id, profile_id, write=True)
    if kind not in ['diagnostic', 'verification']:
        raise ValueError('Invalid assessment type.')
    targets = ordered_concepts(session, [concept_id])
    mastery = {m.concept_id: m for m in mastery_rows(session, user_id, profile_id)}
    ids = []
    for cid in targets:
        current = mastery.get(cid)
        if cid != concept_id and current and current.status == 'Mastered':
            continue
        difficulty = 2 if current and current.score >= .8 else 1
        qs = list(session.scalars(select(Question).where(Question.concept_id == cid,
            Question.phase == kind, Question.difficulty == difficulty).order_by(Question.id)))
        ids.extend(q.id for q in qs[:3])
    if not ids:
        raise ValueError('No questions available for this concept.')
    attempt = Assessment(profile_id=profile_id, kind=kind, question_ids=ids)
    session.add(attempt)
    session.flush()
    return attempt


def get_assessment(session, user_id, assessment_id, write=False):
    attempt = session.get(Assessment, assessment_id)
    if not attempt:
        raise ValueError('Assessment not found.')
    require_profile(session, user_id, attempt.profile_id, write=write)
    return attempt


def refresh_mastery(session, profile_id, concept_id):
    # Latest response for each question, at most 12 unique questions.
    # Repeating one memorized question cannot manufacture mastery.
    records = session.execute(select(Answer, Question).join(Question, Question.id == Answer.question_id)
        .join(Assessment, Assessment.id == Answer.assessment_id)
        .where(Assessment.profile_id == profile_id, Question.concept_id == concept_id)
        .order_by(Assessment.completed_at.desc(), Answer.id.desc())).all()
    unique = {}
    for answer, question in records:
        if question.id not in unique:
            unique[question.id] = (answer, question)
        if len(unique) == 12:
            break
    evidence = len(unique)
    score = sum(a.correct for a, q in unique.values()) / evidence if evidence else 0
    phases = {q.phase for a, q in unique.values()}
    status = 'Mastered' if score >= .8 and evidence >= 6 and len(phases) == 2 else ('Developing' if score >= .5 else 'Needs practice')
    row = session.scalar(select(Mastery).where(Mastery.profile_id == profile_id, Mastery.concept_id == concept_id))
    if not row:
        row = Mastery(profile_id=profile_id, concept_id=concept_id, score=score, evidence=evidence, status=status)
        session.add(row)
    else:
        row.score, row.evidence, row.status, row.updated_at = score, evidence, status, now()
    return row


def submit_assessment(session, user_id, assessment_id, responses):
    attempt = get_assessment(session, user_id, assessment_id, write=True)
    if attempt.completed_at:
        raise ValueError('This assessment has already been submitted.')
    if set(responses) != set(attempt.question_ids):
        raise ValueError('Please answer every question before submitting.')
    questions = {qid: session.get(Question, qid) for qid in attempt.question_ids}
    for qid, choice in responses.items():
        if type(choice) is not int or not 0 <= choice < len(questions[qid].options):
            raise ValueError('Invalid answer choice.')
    # Conditional update protects against double-clicks and concurrent submissions.
    claimed = session.execute(update(Assessment).where(Assessment.id == assessment_id,
        Assessment.completed_at.is_(None)).values(completed_at=now()))
    if claimed.rowcount != 1:
        raise ValueError('This assessment has already been submitted.')
    session.refresh(attempt, attribute_names=["completed_at"])
    correct_count = 0
    for qid, choice in responses.items():
        question = questions[qid]
        correct = choice == question.correct
        correct_count += correct
        session.add(Answer(assessment_id=assessment_id, question_id=qid, selected=choice, correct=correct,
            misconception='' if correct else question.misconceptions.get(str(choice), 'Review this concept.')))
    attempt.score = correct_count / len(questions)
    session.flush()
    for cid in {q.concept_id for q in questions.values()}:
        refresh_mastery(session, attempt.profile_id, cid)
    session.flush()
    build_path(session, user_id, attempt.profile_id)
    session.add(Event(profile_id=attempt.profile_id, kind='Assessment',
        detail=f'{attempt.kind.title()}: {correct_count}/{len(questions)} correct.'))
    from cognify.services.engagement import reward_assessment
    reward_assessment(session,user_id,attempt)
    return attempt


def assessment_feedback(session, user_id, assessment_id):
    attempt = get_assessment(session, user_id, assessment_id)
    return session.execute(select(Answer, Question).join(Question, Answer.question_id == Question.id)
        .where(Answer.assessment_id == attempt.id).order_by(Answer.id)).all()


def history(session, user_id, profile_id):
    require_profile(session, user_id, profile_id)
    return list(session.scalars(select(Assessment).where(Assessment.profile_id == profile_id,
        Assessment.completed_at.is_not(None)).order_by(Assessment.completed_at)))


def report(session, user_id, profile_id):
    require_profile(session, user_id, profile_id)
    names = {c.id: c for c in session.scalars(select(Concept))}
    return [dict(concept=names[m.concept_id].title, concept_id=m.concept_id,
                 subject=names[m.concept_id].subject, mastery=round(m.score*100),
                 evidence=m.evidence, status=m.status) for m in mastery_rows(session, user_id, profile_id)]
