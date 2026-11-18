import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, field_validator
from cognify.models import User, Profile, Classroom, Enrollment, LoginThrottle, now
from cognify.adaptive import EXPERIENCES, PREFERENCES, SUBJECTS, INTERESTS

class AccessDenied(ValueError):
    pass

class ProfileInput(BaseModel):
    nickname: str = Field(min_length=1, max_length=40)
    age_group: str
    education: str = Field(min_length=1, max_length=100)
    interests: list[str] = Field(max_length=8)
    subjects: list[str] = Field(min_length=1, max_length=3)
    goals: str = Field(min_length=1, max_length=500)
    preference: str
    ai_enabled: bool = False

    @field_validator('nickname', 'education', 'goals')
    @classmethod
    def clean_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Please enter a value.')
        return value

    @field_validator('age_group')
    @classmethod
    def valid_age(cls, v):
        if v not in EXPERIENCES:
            raise ValueError('Choose a supported age group.')
        return v

    @field_validator('preference')
    @classmethod
    def valid_preference(cls, v):
        if v not in PREFERENCES:
            raise ValueError('Choose a supported explanation preference.')
        return v

    @field_validator('subjects', 'interests')
    @classmethod
    def valid_choices(cls, values, info):
        allowed = SUBJECTS if info.field_name == 'subjects' else INTERESTS
        if any(v not in allowed for v in values):
            raise ValueError('Unsupported choice.')
        return list(dict.fromkeys(values))

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + digest

def register(session, username, password, role, demo=False):
    username = username.strip().lower()
    if not re.fullmatch(r'[a-z0-9_]{3,40}', username):
        raise ValueError('Use 3–40 lowercase letters, digits or underscores for your username.')
    if not 10 <= len(password) <= 128:
        raise ValueError('Use a password between 10 and 128 characters.')
    if role not in ['learner', 'parent', 'educator']:
        raise ValueError('Invalid role.')
    if session.scalar(select(User).where(User.username == username)):
        raise ValueError('That username is already taken.')
    user = User(username=username, password_hash=password_hash(password), role=role, demo=demo)
    session.add(user)
    session.flush()
    return user

def login(session, username, password):
    username = username.strip().lower()[:40]
    throttle = session.get(LoginThrottle, username)
    if throttle and throttle.blocked_until and throttle.blocked_until > now():
        raise ValueError('Too many attempts. Try again in 15 minutes.')
    user = session.scalar(select(User).where(User.username == username))
    # Perform the same expensive operation for unknown users.
    stored = user.password_hash if user else '0'*32 + ':' + '0'*128
    valid = hmac.compare_digest(password_hash(password[:128], stored.split(':')[0]), stored)
    if not valid or not user or user.demo or len(password) > 128:
        if not throttle:
            throttle = LoginThrottle(username=username, failures=0)
            session.add(throttle)
        if throttle.blocked_until and throttle.blocked_until <= now():
            throttle.failures = 0
        throttle.failures += 1
        if throttle.failures >= 5:
            throttle.blocked_until = now() + timedelta(minutes=15)
        session.commit()  # Failed attempts must survive the caller's error rollback.
        raise ValueError('Username or password is incorrect.')
    if throttle:
        session.delete(throttle)
    return user

def require_user(session, user_id):
    user = session.get(User, user_id)
    if not user:
        raise AccessDenied('Please sign in again.')
    return user

def visible_profiles(session, user_id):
    user = require_user(session, user_id)
    owned = list(session.scalars(select(Profile).where(Profile.owner_id == user.id).order_by(Profile.id)))
    if user.role != 'educator':
        return owned
    shared = list(session.scalars(select(Profile).join(Enrollment, Enrollment.profile_id == Profile.id)
        .join(Classroom, Classroom.id == Enrollment.classroom_id).where(Classroom.educator_id == user.id)))
    return list({p.id: p for p in owned + shared}.values())

def require_profile(session, user_id, profile_id, write=False):
    user = require_user(session, user_id)
    profile = session.get(Profile, profile_id)
    if profile and profile.owner_id == user.id:
        return profile
    if profile and not write and user.role == 'educator':
        shared = session.scalar(select(Enrollment.id).join(Classroom).where(
            Enrollment.profile_id == profile_id, Classroom.educator_id == user.id))
        if shared:
            return profile
    raise AccessDenied('This learner record is not available to your account.')

def create_profile(session, user_id, data: ProfileInput):
    user = require_user(session, user_id)
    if data.age_group in ['5–8', '9–12', '13–17'] and user.role != 'parent' and not user.demo:
        raise ValueError('A parent account must create and manage profiles for learners under 18.')
    profile = Profile(owner_id=user_id, **data.model_dump())
    session.add(profile)
    session.flush()
    return profile

def update_profile(session, user_id, profile_id, data):
    profile = require_profile(session, user_id, profile_id, write=True)
    user = require_user(session, user_id)
    if data.age_group in ['5–8', '9–12', '13–17'] and user.role != 'parent' and not user.demo:
        raise ValueError('A parent account must manage profiles for learners under 18.')
    for key, value in data.model_dump().items():
        setattr(profile, key, value)
    return profile

def create_classroom(session, user_id, name):
    user = require_user(session, user_id)
    if user.role != 'educator':
        raise AccessDenied('Only educator accounts can create classrooms.')
    name = name.strip()
    if not 1 <= len(name) <= 80:
        raise ValueError('Enter a classroom name of 1–80 characters.')
    classroom = Classroom(educator_id=user_id, name=name, invite=secrets.token_urlsafe(18))
    session.add(classroom)
    session.flush()
    return classroom

def enroll(session, user_id, profile_id, invite):
    require_profile(session, user_id, profile_id, write=True)
    classroom = session.scalar(select(Classroom).where(Classroom.invite == invite.strip()))
    if not classroom:
        raise ValueError('Classroom code not found.')
    owner = require_user(session, user_id)
    educator = require_user(session, classroom.educator_id)
    if owner.demo != educator.demo:
        raise AccessDenied('Demo and real classrooms are separate.')
    existing = session.scalar(select(Enrollment).where(Enrollment.classroom_id == classroom.id, Enrollment.profile_id == profile_id))
    if not existing:
        session.add(Enrollment(classroom_id=classroom.id, profile_id=profile_id))
    return classroom

def leave_classroom(session, user_id, profile_id, classroom_id):
    require_profile(session, user_id, profile_id, write=True)
    entry = session.scalar(select(Enrollment).where(Enrollment.profile_id == profile_id, Enrollment.classroom_id == classroom_id))
    if entry:
        session.delete(entry)
