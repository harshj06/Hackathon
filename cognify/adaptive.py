from dataclasses import dataclass

@dataclass(frozen=True)
class Experience:
    label: str
    greeting: str
    instruction: str
    motivation: str
    quiz_label: str
    accent: str
    font_size: int
    plan_minutes: int

EXPERIENCES = {
    '5–8': Experience('Early explorer', 'Let’s discover something!', 'Use short sentences and concrete objects. One small step at a time. Define new words.', 'Every try grows your brain.', 'Tiny challenge', '#6554C0', 19, 5),
    '9–12': Experience('Junior explorer', 'What will you discover today?', 'Use clear everyday language, friendly analogies and small worked steps.', 'Collect discoveries, one concept at a time.', 'Discovery check', '#6554C0', 18, 10),
    '13–17': Experience('Independent learner', 'Make your next breakthrough.', 'Use respectful direct language, define terminology, explain why each step works.', 'Build confidence through evidence.', 'Knowledge check', '#5367AE', 17, 15),
    '18–24': Experience('University learner', 'Turn understanding into capability.', 'Use precise academic language with definitions, intuition and applied examples.', 'Small study sessions. Lasting understanding.', 'Diagnostic assessment', '#376A78', 17, 20),
    '25+': Experience('Lifelong learner', 'Build a skill that opens doors.', 'Use concise professional language and practical applications. Do not assume prior knowledge.', 'Make progress that matters to your goals.', 'Skill check', '#376A78', 17, 20),
}
PREFERENCES = ['Conceptual', 'Visual', 'Auditory', 'Practical']
SUBJECTS = ['Mathematics', 'Science', 'Computing']
INTERESTS = ['Art', 'Music', 'Games', 'Nature', 'Sports', 'Space', 'Technology', 'Business']

NAVIGATION = {
    '5–8': {'My learning':'My discoveries', 'Practice':'Play & learn', 'Progress':'My growth', 'Document lab':'Read together'},
    '9–12': {'My learning':'My discoveries', 'Practice':'Explore & practice'},
    '13–17': {},
    '18–24': {'My learning':'Study plan', 'Practice':'Study & practice'},
    '25+': {'My learning':'Skill plan', 'Practice':'Skill practice'},
}

CAREER_PATHS = {
    'Quantitative foundations': ('Mathematics', 'Use quantities and proportions to explain a budget or compare alternatives.'),
    'Research essentials': ('Science', 'Distinguish observations from explanations and design a fair comparison.'),
    'Programming foundations': ('Computing', 'Break a task into steps and express repeated work as a loop.'),
}


def display_choices(question, age_group):
    count = 2 if age_group == '5–8' else 3 if age_group == '9–12' else 4
    distractors = [i for i in range(len(question.options)) if i != question.correct]
    return sorted([question.correct] + distractors[:count-1])

# Presentation and pacing, not ability labels. Scores always determine skill level.
ENGAGEMENT = {
    '5–8': dict(daily_xp=20, minutes=5, steps=1, reward='Discovery stars', review_days=1, mission='Tiny mission'),
    '9–12': dict(daily_xp=30, minutes=10, steps=2, reward='Explorer XP', review_days=1, mission='Discovery quest'),
    '13–17': dict(daily_xp=40, minutes=15, steps=3, reward='XP', review_days=2, mission='Daily challenge'),
    '18–24': dict(daily_xp=40, minutes=20, steps=3, reward='Skill XP', review_days=2, mission='Study sprint'),
    '25+': dict(daily_xp=30, minutes=20, steps=3, reward='Skill XP', review_days=2, mission='Skill session'),
}
