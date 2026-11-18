# Cognify implementation memory

**Read this file and inspect the actual repository at the start of future sessions.**
Updated 2026-11-18 (UTC). Do not assume a planned feature exists.

## User intent and credential constraint

Build Cognify (Buddy) from an empty workspace: Streamlit, modular Python services,
SQLAlchemy/SQLite, Pandas, Plotly, Pydantic, OpenAI explanations/TTS, five age groups,
deterministic quizzes/mastery, parent and educator views, document learning, tests
and documentation. User will supply the API key and path later. Both
`OPENAI_API_KEY=` and `OPENAI_API_KEY_FILE=` are intentionally blank in `.env` and
`.env.example`. Do not invent a key or treat fake test credentials as operational.

## Current completion status

A working local application is implemented, launched and exercised. Backend and
Streamlit interaction tests pass. Online Responses and TTS integrations exist but
live generation, audio quality, model/account access and connectivity have NOT
been verified with user credentials. Demo intentionally makes no paid API calls.
This is a local release with a finite starter curriculum, not a comprehensive
universal curriculum or a production-hosted SaaS deployment.

## Architecture decisions

- `app.py` owns Streamlit routing/authentication session, cached engine factory and
  idle-session expiration (one hour). Authentication, profile-save and sign-out
  handlers use widget callbacks to avoid stale nested form state after reruns.
- UI calls services with server-side authenticated user ID. Access checks happen in
  services, not merely by hiding navigation. Teacher access is explicit enrollment
  and read-only. Documents remain private to profile owners.
- SQLite foreign keys + WAL, 20-second lock timeout. Mutations use `factory.begin()`.
- Pydantic validates onboarding and structured AI output. AI never scores.
- Accounts use salted scrypt passwords; five failed attempts lock a username for
  15 minutes. Registration does not collect real names, birthdays or emails.
- Real under-18 profiles require a parent account. The adult attests role/age;
  child use is supervised within the parent's session (no separate child login).
- Demo creates an isolated educator account, five synthetic learner profiles, a
  classroom and 18 scored assessments. Demo and real classrooms cannot mix.
- Curriculum: six concepts, 72 stored variants. Mathematics: addition → fractions;
  Science: observation → experiments; Computing: sequence → loops.
- Each concept has three diagnostic and three verification questions at each of
  two levels. Difficulty depends on existing accuracy, not age. Choice presentation
  is 2/3/4 options for early/junior/other groups; the correct index is retained.
- Scores use answer keys. Mastery uses latest answers for up to 12 distinct IDs,
  requiring ≥80%, ≥6 unique questions, and diagnostic + verification evidence.
  Otherwise ≥50% = Developing, <50% = Needs practice. Unassessed stays unassessed.
- Submission claims the assessment with a conditional update before recording
  answers. Answers/mastery/path/history are in one transaction; duplicates fail.
- Prerequisite graph traversal builds persisted remaining paths with cycle checks.
- OpenAI uses official SDK `responses.parse(text_format=Explanation, store=False)`;
  25s timeout, one SDK retry. Refusals/invalid output/errors give labeled fallbacks.
- TTS uses `audio.speech.create(...response_format='mp3')`; up to five audio clips
  are cached per session keyed by profile/text/model/voice. No audio is put in Git.
- Model payload contains age guidance, interests, format, current concept/lesson,
  optionally ≤12,000 characters of source. Scoped chat also sends the current
  question and up to six recent messages. No username or assessment history sent.
- AI text is rendered as literal text to avoid executing embedded Markdown links or
  remote images. Source evidence is always literal text and separate from examples.
- Documents: TXT UTF-8 or text PDF, max 5 MB / 40 PDF pages / 80k extracted chars;
  minimum 30 chars; encrypted/corrupt/empty/oversized inputs rejected. No OCR.
  Exact-word English recall uses deterministic extraction, not model answer keys.
  Document attempt scores are separate from curriculum mastery.
- Static CSS/HTML interpolations escape user fields. Mascot is original inline SVG.
  Visual lessons include plots, counting groups, sequences and comparison tables.
- Adult applied paths persist selected subject and goal; all previous history stays.

## Implemented screens

Landing/demo/sign-in/registration; learner onboarding; five age-adapted workspaces;
subject/concept Practice with diagnostics and verification; Buddy lesson + optional
voice; Progress with Plotly, CSV, assessment history and event history; Document lab;
Parent space with current strengths/weekly activity/offline ideas; Educator studio
with classrooms, invite codes, common practice gaps and individual reports; Settings
with profile edits, AI permission, classroom join/leave and accessibility controls.

Navigation terminology adapts by age. Stars/check counts come from recorded work.
Visual/auditory/conceptual/practical preferences are editable, not fixed diagnoses.
All dashboard numeric analytics come from stored records. Synthetic/class averages
are labeled and exclude unassessed learners. Cross-age formats and different
assessment difficulty mean scores are not appropriate learner rankings.

## Complete project source tree

```text
.env                         local blank credentials (ignored; not shipped)
.env.example                 blank credentials + defaults
.gitignore
.streamlit/config.toml
app.py
requirements.txt
requirements-lock.txt
examples/source-recall.txt
pytest.ini
README.md
memory.md
cognify/
  __init__.py
  config.py
  db.py
  models.py
  adaptive.py
  catalog.py
  services/
    __init__.py
    accounts.py
    learning.py
    buddy.py
    documents.py
    demo.py
    engagement.py
    games.py
    conversation.py
  ui/
    __init__.py
    style.py
    views.py
    routing.py
    experience.py
tests/
  conftest.py
  test_accounts.py
  test_buddy.py
  test_config.py
  test_demo.py
  test_documents.py
  test_learning.py
  test_ui.py
  test_engagement.py
  test_conversation.py
```

Generated/local directories: `.venv/` (initial env reuses system packages),
`work/install-check/` (clean independent venv), `work/` (logs), `data/` (local SQLite),
`outputs/` (source ZIP, guide copy, memory copy, browser preview).
Source was created in the initial release and extended in the engagement upgrade. Source archive excludes data,
credentials, virtual environments, caches and scratch files. The workspace's `.git`
surface points into a parent repository; no broad Git add/commit was performed.

## Database schema

- users: ID, unique username, password hash, role, demo flag, created_at.
- profiles: ID, owner FK, nickname, age_group, education, JSON interests/subjects,
  goals, preference, ai_enabled, created_at.
- classrooms: ID, educator FK, name, unique unpredictable invitation token.
- enrollments: ID, classroom/profile FKs with unique pair.
- concepts: string ID, subject, topic, title, JSON prerequisites and lesson.
- questions: string ID, concept FK, difficulty, phase, prompt, JSON options,
  correct index, JSON misconceptions, explanation.
- assessments: ID, profile FK, kind, question IDs, nullable score, timestamps.
- answers: ID, assessment/question FKs, selected index, correctness, misconception;
  unique assessment/question pair.
- mastery: ID, profile/concept FKs, score, evidence, status, updated_at; unique pair.
- learning_paths: profile FK/PK, ordered JSON concept IDs, updated_at.
- events: ID, profile FK, kind, detail, created_at.
- documents: ID, profile FK, display filename, SHA-256, extracted text, created_at.
- document_attempts: ID, document/profile FKs, correct/total, created_at.
- login_throttles: username PK, failures, blocked_until.

Interests/preferences and subject/topic descriptors are intentionally denormalized;
there are no redundant unused role/subject lookup tables. Additive revision 2 initialization
is supported, but arbitrary schema migrations are not implemented.

## Configuration

Defaults: database `sqlite:///data/cognify.db`; text model `gpt-4.1-mini`;
TTS model `gpt-4o-mini-tts`; voice `coral`; demo allowed. Every model name is
configurable. Key-file path optional, UTF-8, ≤1,024 bytes; direct key takes priority.
`.env` loads from project root. Model defaults are not a claim about this user's
account access. Restart the app after configuration changes.

## Verification actually executed

- Installed pypdf 7.1.0 into `.venv`; installed the complete pinned direct requirements.
- Ran `python -m cognify.db`: database initialized successfully.
- Ran `.venv/bin/python -m compileall -q app.py cognify`: exit 0.
- Ran backend tests first: 29 passed. Found/fixed duplicate distractors in initial
  fractions/loops questions before delivery; local synthetic bank was also repaired.
- Streamlit interaction tests exposed stale widgets during nested form reruns.
  Authentication/profile-save/sign-out were moved to callbacks. Both UI tests pass.
- After age-format/config tests and final literal-text rendering change:
  `.venv/bin/python -m pytest -q`: **33 passed in 6.41s**.
- Created `work/install-check` without system-site-packages and installed all pinned
  requirements successfully from the package index. Clean-environment result:
  **33 passed in 5.55s**; `pip check`: **No broken requirements found**.
  Saved full clean-environment dependency snapshot as `requirements-lock.txt`.
- Started Streamlit on localhost:8501. Health endpoint returned `ok`.
- Browser inspection at initial narrow viewport and desktop 1440×1000; corrected
  header padding. Verified synthetic workspace, adaptive navigation, a three-question
  early-learner diagnostic with 100% correct, offline Buddy explanation and counting
  illustration. Saved `outputs/cognify-preview.jpg`. Restored viewport after testing.
- No live OpenAI calls, paid voice requests, Windows/macOS runtime tests, formal
  accessibility audit, adversarial security audit or educational efficacy study.

## Remaining limitations / known deferred scope

- User credentials/key-file path missing by design; live AI/TTS pending them.
- Six English starter concepts with two difficulty levels. No comprehensive
  technical/university curriculum or automatic general course builder. Typed chat is
  available within the six reviewed curriculum concepts.
- Document quizzes measure exact-word recall, not arbitrary semantic understanding;
  English word extraction only; scanned PDFs need external OCR.
- AI safety uses scope instructions, bounded structured output and no tool access;
  no dedicated moderation pipeline or guarantee of generated factual correctness.
- Supervised parent session, self-attestation and opt-in classroom access; no child
  login separation, verified guardian identity or formal consent-verification system.
- No password recovery, account-deletion UI, automated demo cleanup or schema
  migration framework. SQLite is local and not encrypted by the application.
- PDF parser is in-process; ordinary size limits are not a hardened hostile-file sandbox.
- Accessibility controls are session-scoped. Offline analogies are simple templates.
- Production hosting, security operations and public-service compliance not claimed.
- Development server lifecycle depends on the terminal session; restart with the
  documented launch command if it is no longer running.

## Exact next steps

1. User supplies key/key-file path locally. Fill one credential field and restart.
2. Sign into a real account (not demo), enable online AI for an authorized profile.
3. Settings → Check API connection. Then Learn → optional Buddy explanation → Listen.
   Also verify a typed question in Buddy Chat.
4. Verify structured live explanations, refusal/failure behavior and actual playback.
5. For future expanded curriculum, add reviewed versioned questions/tests; do not
   mutate scoring keys for assessments already administered.
6. Before any public deployment, address the documented identity, child consent,
   moderation, data lifecycle, upload isolation and operational limitations.

## Delivery packaging

Source archive: `outputs/cognify-buddy.zip`. Guide and memory copies also in outputs.
Included an authored source-recall TXT sample. Archive excludes `.env`, all databases,
virtual environments, caches and test logs. Operational credential fields remain blank.

## 2026-11-18 run session

Restarted the existing Streamlit app on 127.0.0.1:8501 at the user's request.
The sandbox initially blocked socket creation; after network permission was granted,
startup succeeded and the health endpoint returned `ok`. No credentials changed.

## 2026-11-18 engagement upgrade — backend phase

New user brief calls for a visual consumer learning experience, games, rewards,
conversational tutoring, study schedules and complete routing. Implementing additions
on top of the verified app; preserving existing records and blank credentials.
Added additive schema v2 tables: rewards, achievements, study_settings, reviews,
game_attempts, lesson_completions, chat_messages, document_plans, schema_versions.
Implemented deterministic XP ledger with unique reward keys, achievement rules,
UTC streaks, daily goals, performance-based review intervals, accessible matching/
ordering/scenario game services for every concept, private concept-scoped chat with
structured AI and honest offline guidance, extractive document summaries and ordered
source missions. Assessment and recall services now issue server-calculated rewards.
UI integration and verification are still in progress; do not assume this phase tested.

## 2026-11-18 engagement upgrade — UI and verification phase

Connected query routes for dashboard, Learn, Buddy Chat, assessments, Games,
Achievements, Study plan, documents, parent, educator, Profile and Settings; dedicated
public login/signup views and safe unauthenticated fallback. Replaced dashboard with
short mission cards, rewards, trail and next-step buttons. Added six interactive visual
models, three-stage lessons, three accessible game modes per concept, private chat,
achievement shelf, XP chart, saved weekly study slots and checkable personal roadmap.
Source missions include extractive summaries and ordered recall; unsupported cloze
sources have a completable reading route. Added weekly parent CSV and educator
mini-lesson recommendations. Existing credentials remain blank.

Intermediate results: 62 tests passed in 13.45s. Browser verified a slider recomputed
3+2=5 to 4+2=6, scenario scored correctly and awarded 25 XP, dashboard increased from
99 to 124 XP/level 2, Momentum badge persisted. Mobile layout checked at 390×844 and
desktop at 1440×1000; saved v2 screenshots in outputs. Current final tests include
additional route/milestone/source edge cases; final results follow below.

Fixed during verification: ORM completed_at needed an explicit refresh after atomic
SQL update before rewarding; chat avatar needed a supported emoji; UI tests needed
fresh widget references after callback navigation. New tables/indexes initialized in
existing local DB after backup to work/cognify-before-engagement-v2.db.


## Final engagement release status — 2026-11-18

The local engagement release is implemented and running at http://127.0.0.1:8501/.
Final development test run: **66 passed in 12.04s**.
Final clean-environment test run: **66 passed in 14.61s**.
Clean-environment `pip check`: **No broken requirements found**.
`compileall` exited 0; running server health endpoint returned `ok`.
All 18 concept/game combinations, replay reward limits, owner privacy, chat fallback,
route access, persisted study milestones, source mission edge cases and full UI
workflows are covered. Browser game/reward and responsive checks are recorded above.

Revision 2 also includes roadmap_progress (profile, checked milestone indices).
The schema additions are documented in the README database table. Existing records
were preserved; no retroactive XP or review schedules are fabricated for old checks.
Games award participation/performance XP but never change assessed mastery. XP is
idempotent per source and bounded per game/concept/day; chat awards no XP. Study
roadmaps are personal preparation checklists, not accredited certification issuance.
Public success-story cards are explicitly illustrative, not customer testimonials.

The current screens add Learn, Games, Buddy Chat, Achievements, Study plan and Profile
to the original views. New demos include completed games, lesson completions and
sample documents through the same persistence services. All numeric analytics use
persisted records, with demo records explicitly synthetic.

Remaining work requires credentials for live AI/TTS verification. Large-scale load,
formal security/accessibility reviews, a broader curriculum and public deployment
remain outside this verified local release. No production-scale or efficacy claims.
The downloadable source and README/memory copies are refreshed in outputs; the
archive excludes local credentials, databases, backups and environments.
