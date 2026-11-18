"""Reviewed starter curriculum. Age changes presentation, never the answer key."""
from cognify.models import Concept, Question

CATALOG = [
    ('addition', 'Mathematics', 'Number sense', 'Adding quantities', [],
     'Addition combines quantities. Count the first group, then count forward by the second group.',
     'Three counters and two counters make five counters: 3 + 2 = 5.',
     'Draw two groups of dots. Move them into one group and count all the dots.',
     'Use beans or coins to build two groups, combine them, and check the total.'),
    ('fractions', 'Mathematics', 'Number sense', 'Fractions as equal parts', ['addition'],
     'A fraction describes equal parts of one whole. The denominator counts all equal parts; the numerator counts the parts selected.',
     'If a whole has 4 equal parts and you select 3, the fraction is 3/4.',
     'Draw a rectangle split into four equal boxes. Shade three boxes to show 3/4.',
     'Fold paper into four equal parts. Shade one part, then two. Compare 1/4 and 2/4.'),
    ('observation', 'Science', 'Scientific thinking', 'Observation and evidence', [],
     'An observation describes something you can notice or measure. An explanation proposes why it happened. Evidence helps test explanations.',
     '“The plant is 12 cm tall” is an observation. “It grew because of sunlight” is an explanation to test.',
     'Make two columns: what you measured, and what you think might explain it.',
     'Observe an object. Write three measurable facts and one question you could investigate.'),
    ('experiments', 'Science', 'Scientific thinking', 'Fair experiments', ['observation'],
     'A fair experiment changes one factor while keeping other important conditions the same. Measure the outcome and repeat the comparison.',
     'To test light and plant growth, vary light but keep plant type, soil and water the same.',
     'Draw two plant pots. Label what changes and circle everything that stays the same.',
     'Plan a paper airplane test. Change one fold, keep paper and throwing method alike, and measure distance.'),
    ('sequence', 'Computing', 'Programming foundations', 'Sequences and algorithms', [],
     'An algorithm is a clear sequence of steps for a task. Order matters because each step can depend on an earlier step.',
     'To save a new document: open an editor, write text, then save the file.',
     'Draw boxes for each step and arrows showing the order.',
     'Write exact instructions for drawing a square. Ask someone to follow only those instructions.'),
    ('loops', 'Computing', 'Programming foundations', 'Loops and repetition', ['sequence'],
     'A loop repeats a set of instructions. A counted loop repeats a known number of times. Count both repetitions and actions within each repetition.',
     'Repeating “draw one dot” four times draws four dots. Repeating “draw two dots” four times draws eight.',
     'Draw an arrow returning to the start of a step and label it with the repetition count.',
     'Write a repeated drawing pattern, then replace the repeated steps with a loop instruction.'),
]

def question_data(cid, n, level):
    if cid == 'addition':
        a, b = (n + 1, n + level + 1) if level == 1 else (n * 7 + 13, n * 3 + 9)
        return f'What is {a} + {b}?', [str(a+b), str(a+b-1), str(a), str(a+b+1)], 'Combine both quantities and count each item once.', ['Check whether one item was skipped.', 'Both groups contribute to the total.', 'Check whether an item was counted twice.']
    if cid == 'fractions':
        total, chosen = n + 4, n + 1
        if level == 1:
            return f'A whole is split into {total} equal parts. You select {chosen}. What fraction is selected?', [f'{chosen}/{total}', f'{total}/{chosen}', f'{chosen}/{total-chosen}', f'{chosen+1}/{total}'], 'The numerator counts selected parts; the denominator counts all equal parts.', ['The numerator and denominator may be reversed.', 'The denominator counts all parts, not just the remaining parts.', 'The numerator must count every selected part.']
        return f'Which is equivalent to {chosen}/{total}?', [f'{chosen*2}/{total*2}', f'{chosen+2}/{total+2}', f'{chosen*2}/{total}', f'{chosen}/{total*2}'], 'Multiply numerator and denominator by the same number to keep the proportion unchanged.', ['Adding the same number does not preserve the fraction.', 'Changing only the numerator changes the value.', 'Changing only the denominator changes the value.']
    if cid == 'observation':
        objects = ['plant', 'seedling', 'flower', 'tree', 'stem', 'leaf']
        obj = objects[n % len(objects)]
        if level == 1:
            return f'Which statement about a {obj} is an observation?', [f'The {obj} measures {n+3} cm.', f'The {obj} likes music.', f'The {obj} will grow fastest tomorrow.', f'The {obj} grew because it was happy.'], 'A measured length is directly observable; the other statements need evidence.', ['An interpretation is different from a measurement.', 'A prediction is not a present observation.', 'A proposed cause needs testing.']
        return f'You measure a {obj} before and after watering. What does a change in height establish by itself?', ['Its measured height changed.', 'Water is the only possible cause.', 'All plants behave the same way.', 'No further tests are useful.'], 'A measurement establishes an observation, not an isolated cause or a universal rule.', ['An observed change does not isolate the cause.', 'One observation does not establish a universal rule.', 'Repeated comparisons can strengthen evidence.']
    if cid == 'experiments':
        pairs = [('light', 'plant growth', 'water amount'), ('water amount', 'plant growth', 'light'), ('paper type', 'airplane distance', 'throwing method'), ('ramp height', 'toy car distance', 'car type'), ('soil type', 'plant growth', 'water amount'), ('wing shape', 'airplane distance', 'paper type')]
        change, outcome, fixed = pairs[n % len(pairs)]
        if level == 1:
            return f'To test how {change} affects {outcome}, what should you do with {fixed}?', ['Keep it the same.', 'Change it each time.', 'Ignore it.', 'Never record the outcome.'], 'Keep other important factors the same so comparisons can isolate the factor being tested.', ['Changing multiple factors makes the cause unclear.', 'Uncontrolled conditions can affect results.', 'An experiment needs a measured outcome.']
        return f'A test of {change} and {outcome} gives different results each trial. What is the best next step?', ['Repeat comparable trials and examine variation.', 'Keep only the best result.', 'Change every condition at once.', 'Claim the first result is always true.'], 'Repeated comparable trials help estimate variation; keep the complete record.', ['Selecting only a favorable result biases the evidence.', 'Changing several conditions prevents a fair comparison.', 'One trial is not enough for a universal claim.']
    if cid == 'sequence':
        tasks = [('save a document', 'Open editor → write text → save', 'Save → write text → open editor'), ('make toast', 'Put bread in toaster → toast → serve', 'Serve → toast → put bread in toaster'), ('plant a seed', 'Prepare soil → plant seed → water', 'Water → harvest → plant seed'), ('send a letter', 'Write → address envelope → send', 'Send → write → address envelope'), ('paint a picture', 'Prepare paper → paint → let dry', 'Let dry → prepare paper → paint'), ('run a program', 'Write instructions → run → inspect output', 'Inspect output → run → write instructions')]
        task, right, wrong = tasks[n % len(tasks)]
        if level == 1:
            return f'Which sequence makes sense to {task}?', [right, wrong, 'Do the final step first.', 'Order never matters.'], 'Prerequisite steps must happen before the steps that depend on them.', ['A later step depends on an earlier one.', 'The last step requires prior preparation.', 'Algorithms depend on the order of instructions.']
        return f'An algorithm to {task} fails at a step requiring an earlier result. What should you check first?', ['Whether the prerequisite step ran successfully.', 'Whether the font is colorful.', 'Whether every step can be skipped.', 'Whether reversing all steps always fixes it.'], 'Trace the sequence and check that each dependency is satisfied.', ['Appearance does not establish correct order.', 'Skipping required steps loses necessary results.', 'Reversing all steps is not a general fix.']
    repeats, actions = n + 2, level + 1
    return f'A loop repeats {repeats} times. Each repetition draws {actions} dots. How many dots are drawn?', [str(repeats*actions), str(repeats*actions-1), str(repeats), str(repeats*actions+actions)], 'Count actions in each repetition: repetitions × dots per repetition.', ['Check whether one action was skipped while counting the repeated groups.', 'Each repetition can perform more than one action.', 'Check for one extra repetition.']

def seed_catalog(session):
    for cid, subject, topic, title, pre, explanation, example, visual, activity in CATALOG:
        if not session.get(Concept, cid):
            session.add(Concept(id=cid, subject=subject, topic=topic, title=title, prerequisites=pre,
                lesson=dict(explanation=explanation, example=example, visual=visual, activity=activity)))
    session.flush()
    for cid, *_ in CATALOG:
        for level in [1, 2]:
            for n in range(6):
                qid = f'{cid}-{level}-{n}'
                if session.get(Question, qid):
                    continue
                prompt, options, rationale, gaps = question_data(cid, n, level)
                # Rotate keys to avoid making the first option a scoring shortcut.
                rotation = n % 4
                rotated = options[rotation:] + options[:rotation]
                correct = (4 - rotation) % 4
                misconceptions = {str(rotated.index(options[i+1])): gaps[i] for i in range(3)}
                session.add(Question(id=qid, concept_id=cid, difficulty=level,
                    phase='diagnostic' if n < 3 else 'verification', prompt=prompt,
                    options=rotated, correct=correct, misconceptions=misconceptions, explanation=rationale))
