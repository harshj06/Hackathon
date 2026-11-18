"""Server-authoritative game state, evidence and transactional rewards."""
import hashlib
import json
import random
from datetime import timedelta
from zoneinfo import ZoneInfo
from datetime import timezone
from fastapi import HTTPException
from sqlalchemy import select
from .storage import Attempt, Reward, Mastery, Receipt, utcnow
from .content import PACKS

def india_date(at=None):
    return (at or utcnow()).replace(tzinfo=timezone.utc).astimezone(ZoneInfo('Asia/Kolkata')).date()

def get_pack(topic):
    if topic not in PACKS:
        raise HTTPException(404, 'This topic does not have a published learning pack yet.')
    return PACKS[topic]

def challenge(attempt: Attempt) -> dict | None:
    if attempt.completed:
        return None
    pack = get_pack(attempt.topic)
    index = len(attempt.answers)
    qid = attempt.question_ids[index]
    # Stable randomization makes retries repeatable while keeping keys server-only.
    rng = random.Random(attempt.id + str(index))
    if attempt.mode == 'puzzle':
        values = list(range(len(pack.sequence)))
        rng.shuffle(values)
        return dict(kind='order', prompt='Build the path in the right order', options=[dict(id=str(i), text=pack.sequence[i]) for i in values])
    if attempt.mode == 'match':
        values = list(range(len(pack.pairs)))
        rng.shuffle(values)
        return dict(kind='match', prompt=pack.pairs[qid][0], options=[dict(id=str(i), text=pack.pairs[i][1]) for i in values])
    question = pack.questions[qid]
    values = list(range(len(question.options)))
    rng.shuffle(values)
    return dict(kind='choice', prompt=question.prompt, options=[dict(id=str(i), text=question.options[i]) for i in values])

def state(attempt: Attempt) -> dict:
    return dict(id=attempt.id, topic=attempt.topic, mode=attempt.mode, completed=attempt.completed, step=len(attempt.answers), total=len(attempt.question_ids), correct=sum(a['correct'] for a in attempt.answers), challenge=challenge(attempt))

def award(session, learner_id: str, source: str, xp: int, coins: int) -> dict:
    existing = session.scalar(select(Reward).where(Reward.learner_id==learner_id, Reward.source==source))
    if existing:
        return dict(xp=0, coins=0)
    session.add(Reward(learner_id=learner_id, source=source, xp=xp, coins=coins))
    return dict(xp=xp, coins=coins)

def respond(session, attempt: Attempt, sequence: int, answer: list[str], key: str) -> dict:
    fingerprint = hashlib.sha256(json.dumps([attempt.id, sequence, answer]).encode()).hexdigest()
    receipt_key = attempt.learner_id + ':' + key
    previous = session.get(Receipt, receipt_key)
    if previous:
        if previous.fingerprint != fingerprint:
            raise HTTPException(409, 'This request key was already used for a different answer.')
        return previous.result
    if attempt.completed or sequence != len(attempt.answers):
        raise HTTPException(409, 'This challenge has already moved on. Resume the saved round.')
    pack = get_pack(attempt.topic)
    qid = attempt.question_ids[sequence]
    if attempt.mode == 'puzzle':
        expected = [str(i) for i in range(len(pack.sequence))]
        if sorted(answer) != expected:
            raise HTTPException(422, 'Use every step exactly once.')
        correct = answer == expected
        explanation = ' → '.join(pack.sequence)
    elif attempt.mode == 'match':
        if len(answer)!=1 or answer[0] not in [str(i) for i in range(len(pack.pairs))]:
            raise HTTPException(422, 'Choose one answer tile.')
        correct = answer[0] == str(qid)
        explanation = pack.pairs[qid][0] + ': ' + pack.pairs[qid][1]
    else:
        question = pack.questions[qid]
        if len(answer)!=1 or answer[0] not in [str(i) for i in range(len(question.options))]:
            raise HTTPException(422, 'Choose one answer portal.')
        correct = answer[0] == str(question.correct)
        explanation = question.explanation
    hinted = sequence in attempt.hints
    attempt.answers = [*attempt.answers, dict(correct=correct, hinted=hinted)]
    attempt.completed = len(attempt.answers) == len(attempt.question_ids)
    # Only independent question responses contribute to mastery, not puzzle replays.
    if attempt.mode in ('battle','boss','timed','placement'):
        mastery = session.scalar(select(Mastery).where(Mastery.learner_id==attempt.learner_id, Mastery.topic==attempt.topic))
        if not mastery:
            mastery = Mastery(learner_id=attempt.learner_id, topic=attempt.topic, evidence={})
            session.add(mastery)
        mastery.evidence = {**mastery.evidence, str(qid): bool(correct and not hinted)}
        accuracy = sum(mastery.evidence.values())/len(mastery.evidence)
        mastery.due = utcnow()+timedelta(days=7 if accuracy>=.8 and len(mastery.evidence)>=4 else 2 if accuracy>=.5 else 1)
    rewards = dict(xp=0, coins=0)
    if attempt.completed:
        accuracy = sum(a['correct'] for a in attempt.answers)/len(attempt.answers)
        rewards = award(session, attempt.learner_id, f'{india_date()}:{attempt.topic}:{attempt.mode}', 10+round(20*accuracy), 5+round(10*accuracy))
    result = dict(**state(attempt), feedback=dict(correct=correct, explanation=explanation), rewards=rewards)
    session.add(Receipt(key=receipt_key, fingerprint=fingerprint, result=result))
    return result
