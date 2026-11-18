"""Authored starter packs. Answer keys never leave the grading boundary."""
from pydantic import BaseModel, Field, model_validator

class Question(BaseModel):
    prompt: str
    options: list[str] = Field(min_length=3, max_length=4)
    correct: int = Field(ge=0, le=3)
    hint: str
    explanation: str

    @model_validator(mode='after')
    def answer_in_options(self):
        if self.correct >= len(self.options) or len(set(self.options)) != len(self.options):
            raise ValueError('Answer options must be distinct and contain the answer key.')
        return self

class Pack(BaseModel):
    id: str
    title: str
    icon: str
    category: str
    description: str
    lesson: str
    activity: str
    questions: list[Question] = Field(min_length=4, max_length=10)
    sequence: list[str] = Field(min_length=3, max_length=6)
    pairs: list[tuple[str, str]] = Field(min_length=3, max_length=6)

    @model_validator(mode='after')
    def unique_items(self):
        if len(set(self.sequence)) != len(self.sequence):
            raise ValueError('Sequence steps must be distinct.')
        if len({p[0] for p in self.pairs}) != len(self.pairs) or len({p[1] for p in self.pairs}) != len(self.pairs):
            raise ValueError('Matching pairs must be unambiguous.')
        return self

def question(prompt: str, options: list[str], hint: str, explanation: str) -> Question:
    return Question(prompt=prompt, options=options, correct=0, hint=hint, explanation=explanation)

PACKS = {p.id: p for p in [
    Pack(id='coding', title='Think like a coder', icon='⌘', category='Technology', description='Turn a big idea into small, clear instructions.',
         lesson='An algorithm is a set of steps for a task. A sequence puts the steps in order. A loop repeats steps; a condition chooses what happens next. Debugging means finding why the actual result differs from the intended result.',
         activity='Write three instructions for making a paper airplane. Ask someone to follow them exactly. Improve one unclear instruction.',
         questions=[question('A robot must wave five times. Which instruction is clearest?', ['Repeat “wave” five times','Wave sometimes','Wave until bored'], 'Think about a precise repetition count.', 'A loop repeats an instruction a specified number of times.'),
                    question('A program reads a file. What must happen first?', ['The file must exist','The text color must change','The keyboard must be unplugged'], 'What does reading depend on?', 'A dependency must be satisfied before the step that needs it.'),
                    question('A loop draws 3 dots per round for 4 rounds. How many dots?', ['12','7','1'], 'Count equal groups, not just the two numbers.', 'Four groups of three make twelve.'),
                    question('What is a useful first step when a program gives the wrong result?', ['Compare expected and actual behavior','Delete every line','Ignore the result'], 'Look for evidence of where the difference begins.', 'Debugging begins by reproducing and understanding the difference.')],
         sequence=['Define the task','Write the steps','Run and check the result'], pairs=[('Loop','Repeated steps'),('Condition','A choice based on a test'),('Sequence','Steps in order')]),
    Pack(id='cooking', title='Kitchen confidence', icon='🥣', category='Everyday skills', description='Learn the habits behind a calmer kitchen.',
         lesson='Read a recipe before starting. Measure ingredients, gather tools and prepare your workspace. Keep raw ingredients separate from ready-to-eat food and wash hands and surfaces. Heat and sharp tools need care; children should work with an adult. A recipe ratio scales all ingredients together.',
         activity='Without using heat or sharp tools, organize ingredients for a simple snack. Explain which preparation step saves time.',
         questions=[question('What helps you avoid surprises while cooking?', ['Read the entire recipe first','Begin with the last step','Guess all quantities'], 'Find out what you need before you begin.', 'Reading the recipe reveals tools, ingredients and preparation steps.'),
                    question('A recipe uses 2 cups for 4 servings. How much for 8 servings?', ['4 cups','2 cups','8 cups'], 'The servings doubled. Apply the same scale to the ingredient.', 'Doubling servings doubles each ingredient: 2 × 2 = 4 cups.'),
                    question('Why keep raw ingredients away from ready-to-eat food?', ['To reduce cross-contamination','To make food look brighter','To change its weight'], 'Think about what could transfer between foods.', 'Separating foods reduces the transfer of harmful microorganisms.'),
                    question('Which is the best preparation habit?', ['Gather and measure ingredients before starting','Search for tools while food burns','Skip washing hands'], 'Reduce interruptions before the cooking begins.', 'Preparation makes the steps easier to follow and safer to manage.')],
         sequence=['Read the recipe','Gather and measure ingredients','Follow the recipe steps'], pairs=[('Measure','Check the quantity'),('Prepare','Get ingredients and tools ready'),('Scale','Change quantities by the same factor')]),
    Pack(id='music', title='Find your rhythm', icon='♫', category='Creative skills', description='Hear patterns. Feel the beat. Make something yours.',
         lesson='A beat is a steady pulse. Rhythm is the pattern of sounds and silences over that pulse. Tempo describes how fast the pulse moves. Pitch describes how high or low a sound is. A rest is a deliberate silence, and it is part of the music.',
         activity='Tap a steady pulse on your knee. Clap twice, pause twice, then repeat while keeping the pulse steady.',
         questions=[question('What does tempo describe?', ['How fast the beat moves','How high a note sounds','The color of an instrument'], 'Imagine a song played faster without changing its notes.', 'Tempo is the speed of the musical pulse.'),
                    question('What is a rest?', ['A deliberate silence','A louder note','A new instrument'], 'Silence can be counted as part of a pattern.', 'A rest specifies silence within the rhythm.'),
                    question('What changes when a note gets higher?', ['Pitch','The number of instruments','The lyrics'], 'Compare a low hum with a high whistle.', 'Pitch is the perceived highness or lowness of a sound.'),
                    question('Which describes rhythm?', ['A pattern of sounds and silences','Only loud sounds','Only the speed'], 'Think about how sounds are arranged over the beat.', 'Rhythm organizes sound and silence in time.')],
         sequence=['Find a steady beat','Clap a short pattern','Repeat while keeping the beat'], pairs=[('Tempo','Speed of the beat'),('Pitch','High or low sound'),('Rest','Silence in the pattern')]),
    Pack(id='science', title='Curiosity lab', icon='🔬', category='Discovery', description='Ask better questions about the world around you.',
         lesson='An observation is something noticed or measured. A prediction describes what you expect to happen. An explanation proposes why it happens. In a fair comparison, change one factor, keep important other conditions alike, and measure the outcome. Repeating measurements helps reveal variation.',
         activity='Observe a plant or object nearby. Write two observations and one question. Keep your observations separate from your explanation.',
         questions=[question('Which statement is an observation?', ['The plant is 12 cm tall','The plant is happy','The plant will grow tomorrow'], 'Choose something that can be measured now.', 'Height is a measurement; happiness and future growth are different kinds of claims.'),
                    question('Testing light and plant growth, what should stay alike?', ['Water amount and plant type','Nothing','Only the labels'], 'Change one factor while keeping other important conditions similar.', 'Keeping water and plant type alike helps isolate the effect of light.'),
                    question('Why repeat a measurement?', ['To see variation and improve confidence','To guarantee your guess is right','To hide unusual results'], 'One observation might not represent the whole pattern.', 'Repeated measurements reveal variability instead of hiding it.'),
                    question('“The ice will melt faster in sunlight” is what?', ['A prediction','A recorded measurement','A proven result'], 'This statement describes what is expected to happen.', 'Predictions concern expected outcomes and can be tested.')],
         sequence=['Ask a testable question','Make a fair comparison','Record and compare results'], pairs=[('Observation','Something noticed or measured'),('Prediction','An expected outcome'),('Explanation','A proposed reason')]),
    Pack(id='communication', title='Say it clearly', icon='💬', category='Life skills', description='Build confidence in everyday conversations.',
         lesson='Clear communication starts with a purpose and an audience. Use concrete words, listen without preparing your reply, and check understanding. A useful message states the main point, gives the detail needed to act, and invites questions. Feedback is more helpful when it describes a specific action.',
         activity='Explain a hobby in three sentences to someone unfamiliar with it. Ask them which part was clearest.',
         questions=[question('Which instruction is most concrete?', ['Please send the two-page draft by Friday','Do it soon','Make it good'], 'Look for a clear action and timeframe.', 'The specific deliverable and deadline make the request actionable.'),
                    question('How can you check you understood someone?', ['Summarize their point and ask if it is right','Interrupt with a new topic','Assume your first guess is correct'], 'Give the speaker a chance to correct your understanding.', 'A short summary helps both people notice misunderstandings.'),
                    question('Which feedback is most useful?', ['Your example helped me understand the main idea','You are always perfect','Everything is bad'], 'Name a specific action and its effect.', 'Specific feedback tells the person what worked and why.'),
                    question('What should a clear message usually lead with?', ['Its main point','Every background detail','An unrelated story'], 'Help the listener understand why you are speaking.', 'Starting with the main point gives the details a purpose.')],
         sequence=['Choose your main point','Add the needed details','Check understanding'], pairs=[('Audience','Who receives your message'),('Purpose','What you want to communicate'),('Feedback','Information that helps improve')]),
    Pack(id='numbers', title='Everyday numbers', icon='◒', category='Foundations', description='Make fractions and proportions feel familiar.',
         lesson='A fraction describes equal parts of a whole. The denominator counts all equal parts; the numerator counts selected parts. Ratios compare quantities. To scale a recipe or design, multiply each related quantity by the same factor.',
         activity='Draw a rectangle and divide it into four equal parts. Shade three. Describe the shaded and unshaded portions.',
         questions=[question('Three of eight equal slices are eaten. What fraction is that?', ['3/8','8/3','3/5'], 'Count selected parts over all equal parts.', 'Three selected parts out of eight is 3/8.'),
                    question('Which fraction is equal to one half?', ['2/4','1/4','3/4'], 'Two of four equal parts cover the same share as one of two.', 'Multiplying numerator and denominator by two preserves the fraction.'),
                    question('A pattern has 2 blue beads for each red bead. For 3 red beads, how many blue?', ['6','5','3'], 'Repeat the two-to-one group three times.', 'Three groups of two blue beads give six.'),
                    question('What does a denominator count?', ['All equal parts of the whole','Only selected parts','Only unselected parts'], 'Look below the fraction bar.', 'The denominator describes the size of the equal partition.')],
         sequence=['Split the whole into equal parts','Count all the parts','Count the selected parts'], pairs=[('Numerator','Selected equal parts'),('Denominator','All equal parts'),('One half','One of two equal parts')]),
]}

COSMETICS = [dict(id='classic', title='Starlight', price=0, color='#baa2ff'), dict(id='mint', title='Forest explorer', price=30, color='#83e5bc'), dict(id='sunset', title='Sunset voyager', price=60, color='#ffba82'), dict(id='ocean', title='Ocean dreamer', price=90, color='#88cfff')]

def public_pack(pack: Pack) -> dict:
    return pack.model_dump(exclude={'questions','sequence','pairs'})
