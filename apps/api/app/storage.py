"""Durable domain records; separate database from the legacy prototype."""
import os
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

class Account(Base):
    __tablename__ = 'accounts'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password: Mapped[str]
    role: Mapped[str]

class Session(Base):
    __tablename__ = 'sessions'
    token: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey('accounts.id'))
    expires: Mapped[datetime]

class Learner(Base):
    __tablename__ = 'learners'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(ForeignKey('accounts.id'))
    alias: Mapped[str]
    age: Mapped[str]
    avatar: Mapped[str]
    companion: Mapped[str]
    personality: Mapped[str] = mapped_column(default='encouraging')
    equipped: Mapped[str] = mapped_column(default='classic')
    consent: Mapped[str] = mapped_column(default='not_required')

class TopicRequest(Base):
    __tablename__ = 'topic_requests'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id'))
    topic: Mapped[str]
    status: Mapped[str] = mapped_column(default='awaiting_configuration')

class Attempt(Base):
    __tablename__ = 'attempts'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id'))
    topic: Mapped[str]
    mode: Mapped[str]
    question_ids: Mapped[list] = mapped_column(JSON)
    answers: Mapped[list] = mapped_column(JSON, default=list)
    hints: Mapped[list] = mapped_column(JSON, default=list)
    completed: Mapped[bool] = mapped_column(default=False)
    started: Mapped[datetime] = mapped_column(default=utcnow)

class Reward(Base):
    __tablename__ = 'rewards'
    __table_args__ = (UniqueConstraint('learner_id', 'source'),)
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id'))
    source: Mapped[str]
    xp: Mapped[int]
    coins: Mapped[int]
    created: Mapped[datetime] = mapped_column(default=utcnow)

class Mastery(Base):
    __tablename__ = 'mastery'
    __table_args__ = (UniqueConstraint('learner_id', 'topic'),)
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id'))
    topic: Mapped[str]
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    due: Mapped[datetime] = mapped_column(default=utcnow)

class Inventory(Base):
    __tablename__ = 'inventory'
    __table_args__ = (UniqueConstraint('learner_id', 'cosmetic'),)
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id'))
    cosmetic: Mapped[str]

class Chat(Base):
    __tablename__ = 'chat'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id'))
    topic: Mapped[str]
    response: Mapped[str]
    created: Mapped[datetime] = mapped_column(default=utcnow)

class Activity(Base):
    __tablename__ = 'activity'
    learner_id: Mapped[str] = mapped_column(ForeignKey('learners.id'), primary_key=True)
    last_seen: Mapped[datetime] = mapped_column(default=utcnow)
    seconds: Mapped[int] = mapped_column(default=0)

url = os.getenv('DATABASE_URL', 'sqlite:///./cognify-next.db')
engine = create_engine(url, **({'connect_args': {'check_same_thread': False}} if url.startswith('sqlite') else {}))
factory = sessionmaker(engine, expire_on_commit=False)
