# Cognify · Learn with Buddy

## New local application

The Next.js/FastAPI replacement runs directly on your machine, without Docker.
It currently includes adult registration/sign-in, sessions, learner profiles and
companion selection. The remaining architecture phases are in development; the
Streamlit prototype below remains available separately.

Requirements: Python 3.11+ and Node.js 22+ with npm.

```sh
python scripts/setup.py
python scripts/dev.py
```

Setup installs Python packages into `.venv-local` and web dependencies into
`apps/web/node_modules`. The second command starts both services. Open
http://localhost:3000; API documentation is at http://127.0.0.1:8000/docs.
Ctrl+C stops both processes. SQLite data is saved in `data/cognify-next.db`.
No Redis or PostgreSQL server is needed. AI_API_KEY and AI_ENDPOINT remain empty;
the current local foundation makes no AI calls. Child profile creation is gated
until a real guardian verification method is implemented.

The existing Streamlit application and data have not been replaced.

Cognify is a locally runnable, gamified adaptive learning application built with Streamlit,
Python services, SQLite/SQLAlchemy, Pydantic, Pandas and Plotly. It includes real
accounts, persisted learner records, deterministic assessments, optional OpenAI
explanations and voice, document recall, and parent/classroom progress views.

**The API key and optional key-file path are intentionally blank.** Everything in
the offline workflow works without them. Online generation and voice are implemented
and tested with mocks, but have not been verified against a live OpenAI account.

## What is implemented

- A branded responsive landing page and Buddy SVG mascot, onboarding, navigation,
  error/empty/loading states, high contrast, adjustable text and reduced motion.
- Mission cards, six interactive concept models, three-stage lessons, three learning
  game modes per concept, XP, levels, streaks, seven badges, unlockable scenarios,
  daily goals and persistent review scheduling.
- A private, concept-scoped Buddy Chat with validated online replies and an honestly
  labeled offline guided tutor.
- Saved study days, session duration, daily XP goals and a personal certification/
  course-preparation checklist. No external qualification or exam coverage is claimed.
- Five age groups: 5–8, 9–12, 13–17, 18–24 and 25+. Central configuration adapts
  navigation language, typography, teaching guidance, quiz choice count, suggested
  study duration and motivation. Ability and difficulty depend on quiz evidence.
- Conceptual, visual, auditory and practical preferences that remain editable.
  Lessons include worked examples, illustrations, activities and unscored reflections.
- Six starter concepts and 72 stored question variants across mathematics, science
  and computing. These are a starter curriculum, not a comprehensive school or
  university syllabus.
- Diagnostics, prerequisite checks, possible misconception feedback, verification,
  deterministic mastery, persisted paths and assessment/activity history.
- Adult study goals and three applied starter paths: quantitative foundations,
  research essentials and programming foundations.
- Parent-owned child profiles, weekly activity summaries and offline activities.
- Educator classrooms with private invite codes, opt-in enrollment/revocation,
  class averages, additional-practice lists and individual progress.
- Isolated synthetic demo accounts with all five ages and classroom examples.
  Demo always stays offline, even if a server API key is present.
- PDF/TXT extraction, exact source excerpts, separate study guides, deterministic
  missing-word recall and separate document attempt history.
- Structured OpenAI Responses API explanations, Pydantic validation, bounded
  retries/timeouts, explicit fallback labels and MP3 narration with a session cache.


## Mission-based learning and games

The new learner journey is **Dashboard → Learn → Games → Assessments → Progress**.
Each step offers a working next-step button that carries the selected concept.

- **Dashboard:** persisted XP, level, current UTC streak, daily goal, recommended
  concept, review prompts, learning trail and latest earned badges. New accounts
  start without invented history. Existing accounts retain their prior evidence;
  rewards begin with activities completed after this upgrade.
- **Learn:** Explore / Connect / Try & verify. Move quantities, fractions and loop
  controls; classify an observation; test a sequence; design a one-factor comparison.
  Explorations are unscored. Lesson completion is an explicit learner confirmation,
  worth 5 participation XP once per concept, never proof of mastery.
- **Games:** Match the pairs, Put it in order, and Scenario quest exist for all six
  concepts. Keyboard-accessible select controls avoid mandatory dragging or timing.
  All answer keys and explanations are authored in Python and snapshotted in the
  persisted game round. Incomplete, duplicate and invalid answers are rejected.
  A submitted round cannot be resubmitted. Results explain the correct connections
  and link to a verification check.
- **Unlocks:** foundation scenarios are immediately available. For a dependent
  concept’s scenario, each prerequisite needs either a game score of at least 80%
  or assessed accuracy of at least 50%. Matching/ordering practice remains open.
  Unlocking a game does not grant concept mastery.
- **Buddy Chat:** choose a concept, type a question or use a suggested prompt.
  Online mode uses OpenAI structured replies only when the profile permits it and
  credentials exist. Offline mode routes requests for an example, picture or
  activity to curated material; it is not presented as a general conversational LLM.
  The UI shows up to 12 recent messages; online context uses up to six. Raw messages
  persist locally and are private even from classroom educators. Do not enter
  personal information. Six messages per minute per learner are allowed.
- **Achievements:** seven persisted badges, a level tracker, XP timeline and audit
  ledger. Badges cover a first check, first game, three-day streak, 100 XP, first
  mastered concept, source recall and games across all three subjects. Earned badges
  are not removed for taking a break or later needing practice.
- **Study plan:** choose daily XP, weekdays and duration; view the next two weeks;
  select an applied starter path; save a personal course/certification target and
  checkable milestones. Editing milestone text resets its completion checklist.
  This in-app plan does not schedule emails, notifications or calendar reminders.

### Reward rules and review intervals

XP celebrates engagement and is deliberately separate from mastery:

| Activity | XP | Reward limit |
|---|---:|---|
| Guided lesson completion | 5 | Once per learner/concept |
| Completed assessment | 10 + rounded(20 × accuracy) | Once per concept set + diagnostic/verification type + UTC day |
| Game round | 5 + rounded(20 × accuracy) | Once per concept + mode + UTC day |
| Source recall | 5 + rounded(10 × accuracy) | Once per document + UTC day |
| Completed source mission | 15 | Once per document |

Unique database reward keys prevent duplicate rewards; game/assessment completion
uses a conditional update to prevent double submissions. Replays remain available.
There are no lost lives, expiring XP or obligatory timed challenges. Each 100 XP
advances a level: level = 1 + floor(total XP / 100).

Streaks count consecutive UTC dates with a reward. An active streak can end yesterday
while today is still in progress. Missing a day resets the displayed current streak,
but never deletes XP or badges. Default daily goals and study durations vary by age;
learners/parents may change them. These goals do not imply ability.

After assessment, concepts below 50% are reviewed after 1 day for early/junior learners
or 2 days for other groups. Developing concepts use at least 2 days. Mastered concepts
use at least 7 days, then double their prior interval to a maximum of 30 days. A later
gap shortens the interval. This is a transparent scheduling heuristic, not a clinically
or educationally validated prescription. Existing pre-upgrade assessments are retained;
a new check creates their review schedule.

### Source missions

Document highlights are the first three eligible **exact source sentences**, labeled
as an extractive summary. Read and explain each source step, then complete the recall
check. A mission with word-recall questions requires all source words to be recalled
correctly before its final step can complete. Documents without eligible English
cloze questions use a reading/reflection path instead. Neither route changes concept
mastery. Uploaded claims are not treated as independently verified facts.

### Routes

Routing uses Streamlit query parameters (for example `/?page=games`) and maintains
consistent sidebar navigation and breadcrumbs. Public routes: `home`, `login`,
`signup`. Authenticated routes: `dashboard`, `learn`, `buddy`, `assessments`, `games`,
`progress`, `achievements`, `study-plan`, `documents`, `profile`, `settings`, `parent`,
`educator`. Role restrictions and ownership checks apply independently of the URL.
Unauthenticated requests show sign-in/onboarding; unknown or unauthorized routes fall
back to the learner dashboard. Child-friendly labels map to the same stable routes.

The homepage includes an interactive fraction preview and explicitly fictional
example journeys. There are no invented customer testimonials or efficacy claims.
Parent space also exports a weekly assessment CSV; educator recommendations use the
most common non-mastered concepts among the enrolled learners. Progress includes
first-to-latest differences on repeated question IDs, labeled as descriptive evidence
that may reflect familiarity rather than a causal learning improvement.

## Install and run

The optional `requirements-lock.txt` captures all dependencies from the clean Linux
verification environment; install it instead of `requirements.txt` for that exact
package set.

Use **Python 3.11–3.13**. Linux with Python 3.13.5 was used for verification.
Windows/macOS commands are provided for the same Python workflow but were not
executed on those operating systems. Run all commands from the extracted project
folder (the directory containing `app.py`). Internet is needed to install packages;
no internet is needed for the offline app after installation.

### Windows CMD

```bat
cd /d C:\path\to\cognify
py -3.13 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
copy .env.example .env
python -m cognify.db
python -m streamlit run app.py
```

If Python 3.13 is not installed, use `py -3.12` or `py -3.11` instead.

### Windows PowerShell

```powershell
Set-Location "C:\path\to\cognify"
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m cognify.db
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Activation is optional. If your system permits script activation, use
`.\.venv\Scripts\Activate.ps1`, then run `python` normally. The commands above
work without changing PowerShell execution policy.

### Linux / macOS

```bash
cd /path/to/cognify
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -m cognify.db
python -m streamlit run app.py
```

On distributions where `venv` is unavailable, install your distribution's Python
venv package first. The application initializes tables and curriculum automatically
on launch; the explicit initialization command is useful as an installation check.

Open **http://127.0.0.1:8501**. Stop the server with Ctrl+C. If that port is occupied:

```bash
python -m streamlit run app.py --server.port 8502
```

The default configuration binds only to localhost. Accounts and documents are
stored in `data/cognify.db`, relative to the project root regardless of the shell's
working directory. Keep the database folder writable. Restarting the server preserves
real accounts and records. Browser refresh may require signing in again.

## Demo mode

1. Click **Explore the demo** on the landing page.
2. Select Pip, Nova, Alex, Sam or River in the sidebar to explore all five ages.
3. Visit Practice (called **Play & learn** for early learners), Progress, Parent
   space, Educator studio, Document lab and Settings.
4. Complete a diagnostic, ask Buddy for an explanation, then verify understanding.
5. Demo assessments are genuinely scored and saved in SQLite. All fictional data
   is labeled; each demo launch creates its own account and classroom.

Demo accounts have random inaccessible passwords and are not reusable sign-in
accounts. Their persisted rows remain local, but demo access ends with its session.
Use a registered account for long-term work. Set `COGNIFY_ALLOW_DEMO=false` to hide
the demo entry point on a shared installation.

## Real accounts and complete application flow

1. **Registration.** An adult chooses an adult learner, parent/guardian or educator
   account, a username and a 10–128 character password. No email or date of birth
   is collected. Passwords use salted scrypt hashes. Five failed login attempts
   lock that username for 15 minutes.
2. **Learner onboarding.** Create a nickname, age group, education level, interests,
   subjects, goal and explanation preference. Only a parent account can create a
   real under-18 profile. A parent can manage multiple child profiles. Online AI
   is off by default and can be enabled per profile in Settings.
3. **Adaptive profile.** `adaptive.py` controls wording, visual treatment, navigation,
   choice count and suggested study session duration. Preferences do not establish
   ability, and a preference is never treated as a fixed learning-style diagnosis.
4. **Subject selection.** Open Practice, choose one of your subjects and a concept.
   The starter paths cover addition → fractions, observation → fair experiments,
   and sequences → loops. Adults can save an applied path from Study plan;
   this updates the goal and selected subject while retaining all existing history.
5. **Diagnostic.** Click **Start diagnostic**. A check contains three questions per
   concept plus three for each unmastered prerequisite. Initial difficulty is level
   1 for every age. A concept with at least 80% measured accuracy gets level 2 on
   the next check. Early learners see two choices, juniors three, others four;
   cross-age percentages are therefore not directly comparable.
6. **Misconception detection.** Submit all answers. Python compares selected indices
   with stored answer keys, calculates the result and records possible gaps mapped
   to specific distractors. These are educational suggestions, not medical diagnoses
   or definitive inferences about a learner's thinking.
7. **Personalized explanation.** Click **Explain with Buddy** for the selected
   concept. Without credentials/permission, a curated lesson is shown. With both,
   the service requests a structured explanation from OpenAI, including interest
   context and age guidance. The UI labels the source and any fallback accurately.
   Use the concept illustration or switch explanation preferences in Settings.
8. **Voice narration.** When online AI is permitted and configured, click **Listen
   to this explanation**. MP3 playback appears in the browser. Narration is explicitly
   labeled AI-generated. Up to five clips are cached per session by profile, text,
   model and voice. Demo, absent credentials or denied permission retain text mode.
9. **Verification.** Click **Verify understanding** for a separate question set.
   AI reflections are unscored; only stored quiz keys affect mastery.
10. **Mastery calculation.** Python uses the most recent answer to each distinct
    question, up to 12 unique questions per concept. A concept is **Mastered** only
    at 80% or better, with at least six distinct questions and both diagnostic and
    verification evidence. At 50% or better without all mastery conditions it is
    **Developing**; below 50% it **Needs practice**. No evidence means unassessed.
    Repeating the same question does not increase evidence count. Scores may fall
    when a later response shows a gap. This is a transparent instructional heuristic,
    not a validated psychometric or educational outcome measure.
11. **Path update.** The prerequisite graph is traversed in dependency order.
    Mastered concepts leave the current path; remaining concepts stay available for
    practice. Changing a subject updates the path without erasing evidence.
12. **Analytics.** Progress charts, CSV export and history read persisted rows.
    The accuracy trend spans checks that may differ in subject/difficulty and must
    not be read as a controlled learning-improvement estimate.

Quiz forms prevent incomplete answers; the service validates the exact question set,
choice bounds, ownership and submission status. A conditional database update makes
one submission authoritative and rejects duplicate submissions.

## Parent and educator workflows

**Parent:** Register as Parent / guardian → create a child profile → use the profile
selector to switch children → open Parent space. Weekly summaries count completed
checks in the previous seven days (UTC); strength and practice lists use current
mastery. Offline activities come from the corresponding curriculum concepts. The
parent also controls profile settings and classroom sharing. Child use is supervised
within the parent's session; there is no separate child login or PIN-locked parent UI.

**Educator:** Register as Educator → open Educator studio → create a classroom →
privately share its invitation code. The learner's owner enters that code in Settings
and confirms sharing. The teacher can then read that learner's profile/progress but
cannot submit assessments, edit the profile or read uploaded documents. The owner
can **Leave classroom** to revoke access. Unassessed learners are omitted from
concept averages, not assigned a zero. The UI shows the assessed count in chart
hover details. Demo and real classrooms cannot mix.

## Document-to-learning

Try the included `examples/source-recall.txt`, or upload your own UTF-8 TXT or
text-based PDF in Document lab. File type, PDF signature, bytes,
page count and extracted length are checked. Limits: 5 MB, 40 PDF pages, 80,000
characters, at least 30 usable characters. Encrypted, corrupt, empty and oversized
files receive errors. Scanned PDFs need external OCR; OCR is not included.

The extracted text and metadata are persisted; original binary files are not stored.
Duplicate uploads with the same content are reused within one learner's shelf.
Source evidence is rendered as literal text. The first 12,000 characters are used for
study guides and recall. The online explanation, if requested and permitted, receives
that excerpt; raw account details and assessment history are excluded.

Offline guides provide source-reading strategies. Online guides can explain source
ideas but remain AI-generated and should be checked against the displayed excerpt.
The prompt treats document instructions as untrusted. The model has no tools,
credentials in its input, database access or scoring authority.

A deterministic English cloze generator selects up to three suitable sentences and
removes a word. The answer key is the exact extracted word; comparison trims space
and ignores case. This verifies source recall, not factual truth or broader concept
mastery. Document attempts never alter curriculum mastery. Non-English documents
can be read, but automated recall currently requires English alphabetic words.

## OpenAI configuration — fill in later

Keep these values blank until you supply credentials locally:

```dotenv
OPENAI_API_KEY=
OPENAI_API_KEY_FILE=
```

Set **either** `OPENAI_API_KEY` in `.env` / the process environment, **or**
`OPENAI_API_KEY_FILE` to a UTF-8 text file containing only the key. A direct key takes
precedence. The optional file must be readable by the server and no larger than
1,024 bytes. Do not paste credentials into the app UI or commit them to source control.
The `.env` file, data and audio files are ignored by Git and excluded from the source
archive. This repository has no hardcoded operational key.

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | blank | Server-only OpenAI credential |
| `OPENAI_API_KEY_FILE` | blank | Optional credential-file path |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Structured Responses model |
| `OPENAI_TTS_MODEL` | `gpt-4o-mini-tts` | Speech model |
| `OPENAI_TTS_VOICE` | `coral` | Speech voice |
| `COGNIFY_DATABASE_URL` | `sqlite:///data/cognify.db` | SQLite location |
| `COGNIFY_ALLOW_DEMO` | `true` | Show synthetic demo entry |

Model names are configurable; account availability is checked separately. After
editing `.env`, restart Streamlit. Sign in to a **real** account, enable online AI in
that learner's Settings, and use **Check API connection**. That checks credentials
and model visibility; it is not proof of a successful generation or speech request.
Then request an explanation and narration to verify those endpoints. Missing keys,
refusals, invalid structured responses, timeouts and API errors produce clearly
labeled fallback content. No failed request is reported as a success.

The client has a 25-second request timeout and at most one SDK retry (two attempts
for retryable failures). Pydantic validates the parsed structured response. Responses
use `store=False`; that flag does not establish a separate data-retention guarantee
for your provider account. Logs contain exception types, not raw API errors or keys.

Integration references used:
- [Official structured outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Official Python speech API](https://developers.openai.com/api/reference/python/resources/audio/subresources/speech/methods/create)

## Architecture and directory structure

```text
app.py                         Session routing, authentication UI, resource initialization
cognify/
  config.py                    Environment/credential loading
  db.py                        Engine, SQLite pragmas, session factory, initialization
  models.py                    SQLAlchemy schema
  catalog.py                   Starter curriculum, prerequisites and question keys
  adaptive.py                  Five age experiences, navigation and applied paths
  services/
    accounts.py                Registration, login, profiles, access and classroom sharing
    learning.py                Assessment lifecycle, scoring, mastery, paths and reports
    buddy.py                   Validated explanations, offline fallback, connection and TTS
    documents.py               Bounded extraction, document ownership and exact recall
    demo.py                    Isolated synthetic users/profiles/assessments
    engagement.py              XP ledger, streaks, badges, study plans and review scheduling
    games.py                   Stored matching/order/scenario rounds and deterministic scoring
    conversation.py            Private concept chat and structured reply fallback
  ui/
    style.py                   CSS, cards, hero and original inline SVG mascot
    views.py                   Assessments, documents, reports, profile and settings
    experience.py              Missions, interactive lessons, games, chat and achievement UI
    routing.py                 Query routes and contextual next-step navigation
tests/
  conftest.py                  Isolated database/account fixtures
  test_accounts.py            Authentication, throttling and role/ownership boundaries
  test_learning.py            Keys, scores, prerequisites, evidence and atomic submissions
  test_documents.py           TXT/PDF extraction, invalid files and source-grounded recall
  test_buddy.py               Mocked AI/TTS success and honest fallback paths
  test_config.py              Blank/file credential configuration
  test_demo.py                Five ages, persisted synthetic records and isolation
  test_ui.py                  Streamlit workflows, routing, games/chat/study-plan integration
  test_engagement.py          All 18 game/concept combinations, XP, privacy and schema upgrade
  test_conversation.py        Chat persistence, privacy, structured success and fallback
.streamlit/config.toml        Local server and visual configuration
.env.example                 Blank credential fields, configurable defaults
.gitignore                   Excludes secrets, local data and generated files
requirements.txt             Pinned direct dependencies
requirements-lock.txt        Full clean-environment dependency snapshot
examples/source-recall.txt    Included document-learning sample
pytest.ini                   Test discovery configuration
README.md                    This guide
memory.md                    Persistent implementation and verification context
```

`app.py` holds a server-side session user ID, expires idle sessions after an hour,
and clears private UI caches on profile changes/sign-out. Views call services with
the authenticated user ID. Services verify ownership or authorized enrollment before
reading/writing records. Mutations use SQLAlchemy transaction scopes. Assessment
submission writes answers, recomputes mastery, refreshes paths and appends history
within one transaction. The Buddy service receives a bounded teaching payload and
cannot update scores. Conversation sends a bounded current question and up to six
recent messages in that learner’s concept thread; other learner threads are excluded. Pandas shapes persisted rows for Plotly and CSV export.

### Database schema

| Table | Key data and relationships |
|---|---|
| `users` | Unique username, salted password hash, role, demo flag |
| `profiles` | Owner FK, nickname, age/education, interests, subjects, goal, preference, AI permission |
| `classrooms` | Educator FK, name, unpredictable unique invite code |
| `enrollments` | Unique classroom/profile pair authorizing read access |
| `concepts` | Subject/topic, title, prerequisite IDs and reviewed lesson JSON |
| `questions` | Concept FK, level, phase, prompt/options, correct index, misconception map |
| `assessments` | Profile FK, assigned question IDs, type, score, timestamps |
| `answers` | Unique assessment/question pair, selected index, correctness, possible gap |
| `mastery` | Unique profile/concept pair, score, distinct evidence count, status |
| `learning_paths` | One per profile, ordered remaining concept IDs |
| `events` | Profile activity type, summary and timestamp |
| `documents` | Profile FK, safe display filename, digest, extracted text |
| `document_attempts` | Document/profile FKs, exact-word correct/total counts |
| `login_throttles` | Username attempt count and temporary lockout timestamp |
| `rewards` | Profile, unique source key, category, XP and UTC timestamp |
| `achievements` | Unique profile/badge pair and earned timestamp |
| `game_attempts` | Profile/concept, mode, immutable round payload, responses, score, XP |
| `lesson_completions` | Unique profile/concept completion; participation only |
| `study_settings` | Daily XP target, weekdays, minutes and personal preparation roadmap |
| `roadmap_progress` | Profile and completed milestone indices; reset when roadmap changes |
| `reviews` | Unique profile/concept, next due time and interval |
| `chat_messages` | Private profile/concept thread, role, text and response-source label |
| `document_plans` | Exact source-based step list and ordered completion indices |
| `schema_versions` | Applied additive schema revision |

Interests/preferences and subject/topic definitions are stored as validated JSON or
concept attributes rather than redundant lookup tables. SQLite foreign keys are
on, WAL is enabled and lock timeout is 20 seconds. Schema revision 2 adds new tables and query indexes without dropping or rewriting
existing tables. Startup is idempotent. This is an additive upgrade, not a general
schema-migration framework. Backup the database before installing an upgrade.

## Tests and verification

```bash
python -m pytest -q
python -m compileall -q app.py cognify
```

**66 tests passed in the development environment (12.04s) and in the clean
environment (14.61s). `pip check` found no broken requirements; compilation passed.**

Tests use temporary databases and synthetic users; they do not call paid APIs or
read real user records. The automated suite covers all five age formats, account
registration/onboarding/sign-out/sign-in persistence, every demo screen, quiz
submission, offline Buddy, deterministic assessment rules, failed-login lockouts,
classroom access and revocation, upload boundaries and mocked provider failures.

The browser was also used to inspect the responsive landing/workspace and complete
a live demo diagnostic (100% correct), then render an offline Buddy explanation and
concept illustration. Streamlit's `/_stcore/health` returned `ok`. Live AI/TTS and
Windows/macOS execution remain unverified until those environments are available.
The engagement release was also checked at 1440×1000 and 390×844: an interactive
addition model updated correctly, a scenario awarded 25 XP, and the dashboard
persisted level 2 and its badge. See `memory.md` for execution details.

## Troubleshooting and practical limits

- **Module missing:** use the same virtual-environment Python for installation and
  launch. Prefer `python -m streamlit` to a global `streamlit` executable.
- **Port in use:** choose `--server.port 8502` and open the matching address.
- **Database locked/unwritable:** close other tools editing the file, use one local
  app instance, and confirm write access to `data/`. Backup the database while the
  app is stopped; keep `-wal`/`-shm` sidecars if copying a running SQLite database.
- **API remains offline:** demo deliberately never uses OpenAI. Use a real account,
  enable per-profile permission, configure the key, and restart the server. Check
  model permissions, account limits and connectivity separately.
- **PDF has no text:** export a text-based PDF or perform OCR externally. A TXT
  export is often the simplest alternative.
- **Cannot create a child profile:** use a parent/guardian account. Teacher records
  are shared only after owner enrollment; entering a role does not grant access to
  anyone else's records.
- **Login locked:** wait 15 minutes after five incorrect attempts. Password recovery,
  email verification and external identity providers are not implemented.
- **Mobile header/navigation:** use the Streamlit sidebar toggle on narrow screens;
  content columns stack. Text size and motion settings are session preferences.
- **Deployment scope:** this is a local application, not a hosted multi-tenant SaaS
  deployment. The database is not encrypted by the app. Protect the computer and
  its backups. Parent/age attestation is not identity verification. Before public
  hosting, add an appropriate identity/consent system, deployment protections,
  operational monitoring, data lifecycle controls and a security review.
- **Content scope:** the bundled starter curriculum is finite, English, and has two
  difficulty levels. Offline analogies use simple interest framing. Generated AI
  content is constrained by prompts/schema, not guaranteed factually correct or
  child-safe by a dedicated moderation pipeline. Buddy Chat is limited to selected curriculum concepts, not a general-purpose chat
  assistant. There is no automatic OCR, speech recognition, universal course generator or automatic
  diagnosis. Source recall is deliberately separate from concept mastery.
- **Resource limits:** document byte/page/text limits protect ordinary local use;
  PDF parsing is in-process, not a hardened sandbox for hostile public uploads.
- **Persistence and maintenance:** real profiles survive restarts; sessions do not.
  Demo records are retained locally and are not automatically garbage-collected.
  No account deletion, password reset or arbitrary database migration UI is included.

## Extending the curriculum

Add concepts and prerequisites to `catalog.py`, write reviewed questions with stable
IDs, unique options and deterministic keys, and add tests for correctness and graph
behavior. Initialization adds missing entries; it does not silently rewrite existing
question history. Treat substantive curriculum changes as versioned migrations.
Keep AI reflections unscored and do not let a generated answer key determine mastery.

At the beginning of future development sessions, read `memory.md`, inspect the actual
files, and rerun relevant tests before assuming any planned feature exists.
