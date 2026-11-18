import secrets
from cognify.models import Question, Enrollment
from cognify.services.accounts import register, create_profile, ProfileInput, create_classroom
from cognify.services.learning import start_assessment, submit_assessment
from cognify.adaptive import EXPERIENCES, SUBJECTS


def create_demo(session):
    user = register(session, 'demo_' + secrets.token_hex(6), secrets.token_urlsafe(20), 'educator', demo=True)
    classroom = create_classroom(session, user.id, 'Discovery studio · synthetic classroom')
    for index, age in enumerate(EXPERIENCES):
        profile = create_profile(session, user.id, ProfileInput(nickname=['Pip', 'Nova', 'Alex', 'Sam', 'River'][index],
            age_group=age, education=['Early school', 'Primary school', 'Secondary school', 'University', 'Professional'][index],
            interests=['Space', 'Art'], subjects=SUBJECTS, goals='Understand new ideas and explain them with confidence.',
            preference=['Visual', 'Practical', 'Conceptual', 'Conceptual', 'Auditory'][index]))
        session.add(Enrollment(classroom_id=classroom.id, profile_id=profile.id))
        for concept in ['fractions', 'loops', 'experiments']:
            attempt = start_assessment(session, user.id, profile.id, concept)
            responses = {}
            for i, qid in enumerate(attempt.question_ids):
                q = session.get(Question, qid)
                responses[qid] = q.correct if (i + index) % 4 else (q.correct + 1) % 4
            submit_assessment(session, user.id, attempt.id, responses)
        if index >= 2:
            attempt = start_assessment(session, user.id, profile.id, 'loops', 'verification')
            submit_assessment(session, user.id, attempt.id, {qid: session.get(Question, qid).correct for qid in attempt.question_ids})
        from cognify.services.games import start_game,submit_game
        from cognify.services.documents import upload_document
        from cognify.services.engagement import complete_lesson
        game=start_game(session,user.id,profile.id,'addition','match')
        submit_game(session,user.id,game.id,game.payload['correct'])
        complete_lesson(session,user.id,profile.id,'addition')
        upload_document(session,user.id,profile.id,'Demo source — evidence.txt',
            b'An observation describes something noticed or measured. A fair comparison changes one factor while other important conditions stay alike. Repeated measurements help reveal variation between trials.')
    return user
