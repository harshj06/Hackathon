from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    demo: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)

class Profile(Base):
    __tablename__ = 'profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    nickname: Mapped[str] = mapped_column(String(40))
    age_group: Mapped[str] = mapped_column(String(10))
    education: Mapped[str] = mapped_column(String(100))
    interests: Mapped[list] = mapped_column(JSON)
    subjects: Mapped[list] = mapped_column(JSON)
    goals: Mapped[str] = mapped_column(String(500))
    preference: Mapped[str] = mapped_column(String(30))
    ai_enabled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=now)

class Classroom(Base):
    __tablename__ = 'classrooms'
    id: Mapped[int] = mapped_column(primary_key=True)
    educator_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String(80))
    invite: Mapped[str] = mapped_column(String(64), unique=True)

class Enrollment(Base):
    __tablename__ = 'enrollments'
    __table_args__ = (UniqueConstraint('classroom_id', 'profile_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey('classrooms.id'))
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'))

class Concept(Base):
    __tablename__ = 'concepts'
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    subject: Mapped[str] = mapped_column(String(60))
    topic: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(100))
    prerequisites: Mapped[list] = mapped_column(JSON)
    lesson: Mapped[dict] = mapped_column(JSON)

class Question(Base):
    __tablename__ = 'questions'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey('concepts.id'))
    difficulty: Mapped[int]
    phase: Mapped[str] = mapped_column(String(20))
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON)
    correct: Mapped[int]
    misconceptions: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)

class Assessment(Base):
    __tablename__ = 'assessments'
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'))
    kind: Mapped[str] = mapped_column(String(20))
    question_ids: Mapped[list] = mapped_column(JSON)
    score: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(default=now)
    completed_at: Mapped[datetime | None]

class Answer(Base):
    __tablename__ = 'answers'
    __table_args__ = (UniqueConstraint('assessment_id', 'question_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey('assessments.id'))
    question_id: Mapped[str] = mapped_column(ForeignKey('questions.id'))
    selected: Mapped[int]
    correct: Mapped[bool]
    misconception: Mapped[str] = mapped_column(Text)

class Mastery(Base):
    __tablename__ = 'mastery'
    __table_args__ = (UniqueConstraint('profile_id', 'concept_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'))
    concept_id: Mapped[str] = mapped_column(ForeignKey('concepts.id'))
    score: Mapped[float]
    evidence: Mapped[int]
    status: Mapped[str] = mapped_column(String(30))
    updated_at: Mapped[datetime] = mapped_column(default=now)

class LearningPath(Base):
    __tablename__ = 'learning_paths'
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), primary_key=True)
    concept_ids: Mapped[list] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(default=now)

class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'))
    kind: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=now)

class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'))
    filename: Mapped[str] = mapped_column(String(120))
    digest: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=now)

class DocumentAttempt(Base):
    __tablename__ = 'document_attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id'))
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'))
    correct: Mapped[int]
    total: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=now)

class LoginThrottle(Base):
    __tablename__ = 'login_throttles'
    username: Mapped[str] = mapped_column(String(40), primary_key=True)
    failures: Mapped[int] = mapped_column(default=0)
    blocked_until: Mapped[datetime | None]

# Engagement v2 uses additive tables: existing learner records remain untouched.
class Reward(Base):
    __tablename__ = 'rewards'
    __table_args__ = (UniqueConstraint('profile_id', 'source_key'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), index=True)
    source_key: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(30))
    xp: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=now, index=True)

class Achievement(Base):
    __tablename__ = 'achievements'
    __table_args__ = (UniqueConstraint('profile_id', 'badge'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), index=True)
    badge: Mapped[str] = mapped_column(String(50))
    earned_at: Mapped[datetime] = mapped_column(default=now)

class StudySettings(Base):
    __tablename__ = 'study_settings'
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), primary_key=True)
    daily_xp: Mapped[int] = mapped_column(default=30)
    weekdays: Mapped[list] = mapped_column(JSON, default=lambda:[0,2,4])
    minutes: Mapped[int] = mapped_column(default=15)
    credential_goal: Mapped[str] = mapped_column(String(200), default='')
    roadmap: Mapped[list] = mapped_column(JSON, default=list)

class Review(Base):
    __tablename__ = 'reviews'
    __table_args__ = (UniqueConstraint('profile_id', 'concept_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), index=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey('concepts.id'))
    due_at: Mapped[datetime] = mapped_column(index=True)
    interval_days: Mapped[int] = mapped_column(default=1)

class GameAttempt(Base):
    __tablename__ = 'game_attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), index=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey('concepts.id'))
    mode: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON)
    responses: Mapped[list | None] = mapped_column(JSON)
    score: Mapped[float | None]
    xp: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=now)
    completed_at: Mapped[datetime | None]

class LessonCompletion(Base):
    __tablename__ = 'lesson_completions'
    __table_args__ = (UniqueConstraint('profile_id', 'concept_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), index=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey('concepts.id'))
    completed_at: Mapped[datetime] = mapped_column(default=now)

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'), index=True)
    concept_id: Mapped[str] = mapped_column(ForeignKey('concepts.id'))
    role: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), default='')
    created_at: Mapped[datetime] = mapped_column(default=now)

class DocumentPlan(Base):
    __tablename__ = 'document_plans'
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id'), primary_key=True)
    steps: Mapped[list] = mapped_column(JSON)
    completed: Mapped[list] = mapped_column(JSON, default=list)

class SchemaVersion(Base):
    __tablename__ = 'schema_versions'
    version: Mapped[int] = mapped_column(primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(default=now)

class RoadmapProgress(Base):
    __tablename__ = 'roadmap_progress'
    profile_id: Mapped[int] = mapped_column(ForeignKey('profiles.id'),primary_key=True)
    checked: Mapped[list] = mapped_column(JSON,default=list)

# Indexes support scoped reports and histories as local datasets grow.
from sqlalchemy import Index
Index('ix_assessment_profile_completed',Assessment.profile_id,Assessment.completed_at)
Index('ix_answer_question',Answer.question_id)
Index('ix_events_profile_created',Event.profile_id,Event.created_at)
Index('ix_documents_profile_digest',Document.profile_id,Document.digest)
