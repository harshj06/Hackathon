"""Three accessible game mechanics. No AI output is used as a game answer key."""
import random
from sqlalchemy import select, update
from cognify.models import Concept, Mastery, GameAttempt, Event, now
from cognify.services.accounts import require_profile
from cognify.services.engagement import _award,refresh_badges

# Stable curricular content stored into each attempt to preserve its answer key.
CONTENT={
 'addition':dict(pairs=[('2 + 3','5'),('4 + 2','6'),('3 + 4','7')],
   steps=['Count the first group','Count forward by the second group','Check the combined total'],
   prompt='You collect 4 blue tokens and 3 gold tokens. How many tokens do you have?',options=['7','1','4'],answer=0,
   why='Combine both groups: 4 + 3 = 7.'),
 'fractions':dict(pairs=[('Numerator','Selected equal parts'),('Denominator','All equal parts'),('One half','1 of 2 equal parts')],
   steps=['Split the whole into equal parts','Count all parts for the denominator','Count selected parts for the numerator'],
   prompt='A snack is cut into 8 equal pieces. You eat 3. Which fraction did you eat?',options=['8/3','3/8','3/5'],answer=1,
   why='Three selected parts out of eight equal parts gives 3/8.'),
 'observation':dict(pairs=[('Observation','Something noticed or measured'),('Prediction','An expected future outcome'),('Explanation','A possible reason why')],
   steps=['Choose something to observe','Measure and record what happens','Separate the observation from a possible explanation'],
   prompt='Which statement could go in the measurement column of a notebook?',options=['The plant feels happy','The plant will grow tomorrow','The plant is 12 cm tall'],answer=2,
   why='A measured height is an observation. Feelings and predictions are not this measurement.'),
 'experiments':dict(pairs=[('Changed factor','What you deliberately vary'),('Measured outcome','The result you record'),('Controlled condition','What you keep alike')],
   steps=['Choose one factor to change','Keep other important conditions alike','Measure and compare repeated outcomes'],
   prompt='You test how light affects plant growth. What should stay the same?',options=['The plant type and water amount','Nothing','Both light and water should change'],answer=0,
   why='Vary light while keeping water and plant type alike to make a fair comparison.'),
 'sequence':dict(pairs=[('Algorithm','Clear steps for a task'),('Sequence','The order of steps'),('Dependency','Something needed by a later step')],
   steps=['Open a text editor','Write the instructions','Save the new file'],
   prompt='A program reads a file before it exists. What is a useful first fix?',options=['Change the text color','Create the file before reading it','Ignore every error'],answer=1,
   why='The read step depends on the file having been created.'),
 'loops':dict(pairs=[('Loop','Repeated instructions'),('Iteration','One repetition'),('4 rounds × 2 dots','8 dots')],
   steps=['Set the repetition count to four','Draw two dots in each repetition','Check that eight dots were drawn'],
   prompt='A robot takes 3 steps each round for 4 rounds. How many steps?',options=['7','4','12'],answer=2,
   why='Four groups of three steps total 12 steps.'),
}
MODES={'match':'Match the pairs','order':'Put it in order','scenario':'Scenario quest'}


def unlocked(session,user_id,profile_id,concept_id):
    require_profile(session,user_id,profile_id)
    concept=session.get(Concept,concept_id)
    if not concept:
        raise ValueError('Unknown concept.')
    for prerequisite in concept.prerequisites:
        m=session.scalar(select(Mastery).where(Mastery.profile_id==profile_id,Mastery.concept_id==prerequisite))
        passed=session.scalar(select(GameAttempt.id).where(GameAttempt.profile_id==profile_id,
            GameAttempt.concept_id==prerequisite,GameAttempt.score>=.8).limit(1))
        if not passed and not (m and m.score>=.5):
            return False
    return True


def start_game(session,user_id,profile_id,concept_id,mode):
    require_profile(session,user_id,profile_id,write=True)
    if mode not in MODES or concept_id not in CONTENT:
        raise ValueError('Choose an available game.')
    if mode=='scenario' and not unlocked(session,user_id,profile_id,concept_id):
        raise ValueError('Try a prerequisite game or diagnostic to unlock this quest.')
    content=CONTENT[concept_id]
    rng=random.SystemRandom()
    if mode=='match':
        options=[pair[1] for pair in content['pairs']];rng.shuffle(options)
        payload=dict(prompts=[pair[0] for pair in content['pairs']],options=options,
            correct=[options.index(pair[1]) for pair in content['pairs']],explanation='Each pair connects a term or expression with its meaning.')
    elif mode=='order':
        options=content['steps'][:];rng.shuffle(options)
        payload=dict(prompts=['First','Next','Finally'],options=options,
            correct=[options.index(step) for step in content['steps']],explanation=' → '.join(content['steps']))
    else:
        payload=dict(prompts=[content['prompt']],options=content['options'],correct=[content['answer']],explanation=content['why'])
    attempt=GameAttempt(profile_id=profile_id,concept_id=concept_id,mode=mode,payload=payload)
    session.add(attempt);session.flush()
    return attempt


def get_game(session,user_id,attempt_id,write=False):
    attempt=session.get(GameAttempt,attempt_id)
    if not attempt:
        raise ValueError('Game not found.')
    require_profile(session,user_id,attempt.profile_id,write=write)
    return attempt


def submit_game(session,user_id,attempt_id,responses):
    attempt=get_game(session,user_id,attempt_id,write=True)
    if attempt.completed_at:
        raise ValueError('This round is already complete. Start another to practise again.')
    key=attempt.payload['correct']
    if len(responses)!=len(key) or any(type(v) is not int or not 0<=v<len(attempt.payload['options']) for v in responses):
        raise ValueError('Choose an answer for every card.')
    if attempt.mode in ['match','order'] and len(set(responses))!=len(responses):
        raise ValueError('Use each answer once.')
    claimed=session.execute(update(GameAttempt).where(GameAttempt.id==attempt_id,GameAttempt.completed_at.is_(None)).values(completed_at=now()))
    if claimed.rowcount!=1:
        raise ValueError('This round is already complete.')
    session.refresh(attempt, attribute_names=["completed_at"])
    attempt.responses=responses
    attempt.score=sum(a==b for a,b in zip(key,responses))/len(key)
    attempt.xp=_award(session,attempt.profile_id,f'game:{attempt.concept_id}:{attempt.mode}:{now().date()}',
        'Game',5+round(20*attempt.score))
    session.add(Event(profile_id=attempt.profile_id,kind='Game',detail=f'{MODES[attempt.mode]}: {round(attempt.score*100)}% correct; {attempt.xp} XP.'))
    refresh_badges(session,user_id,attempt.profile_id)
    return attempt
