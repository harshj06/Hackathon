"""Cognify REST boundary. All learner data is ownership checked."""
import hashlib
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from .storage import Base, engine, factory, Account, Session, Learner, utcnow
from .security import hash_password, verify_password, limit

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    from .storage import GeneratedPack
    from .content import Pack, PACKS
    with factory() as session:
        for draft in session.scalars(select(GeneratedPack).where(GeneratedPack.status=='published')):
            pack=Pack.model_validate(draft.payload)
            PACKS[pack.id]=pack
    yield

app = FastAPI(title='Cognify API', version='1.0.0', lifespan=lifespan)

@app.middleware('http')
async def guard(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        configured_origin = os.getenv('APP_ORIGIN', 'http://localhost:3000')
        allowed_origins = {configured_origin}
        if configured_origin in ('http://localhost:3000', 'http://127.0.0.1:3000'):
            allowed_origins.update(('http://localhost:3000', 'http://127.0.0.1:3000'))
        if origin and origin not in allowed_origins:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Origin not permitted'}, status_code=403)
        if request.headers.get('x-cognify-request') != '1':
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Request header required'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response

def db():
    with factory.begin() as session:
        # SQLite has no row locks. Serialize writes (and ownership reads) to keep
        # retries, rewards and coin purchases atomic in this single local service.
        if engine.dialect.name == 'sqlite':
            session.execute(text('BEGIN IMMEDIATE'))
        yield session

def current(request: Request, session=Depends(db)) -> Account:
    token = hashlib.sha256(request.cookies.get('cognify_session', '').encode()).hexdigest()
    auth = session.get(Session, token)
    if not auth or auth.expires < utcnow():
        raise HTTPException(401, 'Please sign in.')
    limit(auth.account_id)
    return session.get(Account, auth.account_id)

def owned(session, account: Account, learner_id: str) -> Learner:
    learner = session.scalar(select(Learner).where(Learner.id == learner_id, Learner.account_id == account.id).with_for_update())
    if not learner:
        raise HTTPException(404, 'Learner not found.')
    return learner

class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    role: Literal['learner', 'parent'] = 'learner'
    adult: bool = False

def issue(response: Response, session, account: Account):
    token = secrets.token_urlsafe(32)
    session.add(Session(token=hashlib.sha256(token.encode()).hexdigest(), account_id=account.id, expires=utcnow()+timedelta(hours=12)))
    response.set_cookie('cognify_session', token, httponly=True, secure=os.getenv('APP_ORIGIN','').startswith('https:'), samesite='strict', max_age=43200)
    return {'id': account.id, 'role': account.role}

@app.post('/api/v1/auth/register', status_code=201)
def register(body: Credentials, request: Request, response: Response, session=Depends(db)):
    limit('register:' + (request.client.host if request.client else 'unknown'), 10)
    if not body.adult:
        raise HTTPException(422, 'An adult must create the account. Ask a parent or guardian to help.')
    email = body.email.strip().lower()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        raise HTTPException(422, 'Enter a valid email address.')
    account = Account(email=email, password=hash_password(body.password), role=body.role)
    session.add(account)
    try:
        session.flush()
    except IntegrityError:
        raise HTTPException(409, 'Unable to create this account. Try signing in.')
    return issue(response, session, account)

@app.post('/api/v1/auth/login')
def login(body: Credentials, request: Request, response: Response, session=Depends(db)):
    limit('login:' + (request.client.host if request.client else 'unknown'), 10)
    account = session.scalar(select(Account).where(Account.email == body.email.strip().lower()))
    stored = account.password if account else '0'*32+':'+'0'*128
    valid = verify_password(body.password, stored)
    if not account or not valid:
        raise HTTPException(401, 'Email or password is incorrect.')
    return issue(response, session, account)

@app.post('/api/v1/auth/logout')
def logout(request: Request, response: Response, account=Depends(current), session=Depends(db)):
    token = hashlib.sha256(request.cookies['cognify_session'].encode()).hexdigest()
    session.delete(session.get(Session, token))
    response.delete_cookie('cognify_session')
    return {'ok': True}

@app.get('/api/v1/me')
def me(account=Depends(current)):
    return {'id': account.id, 'role': account.role}

class LearnerInput(BaseModel):
    alias: str = Field(min_length=1, max_length=30, pattern=r'^[\w -]+$')
    age: Literal['8–14', '15–17', '18+'] = '18+'
    avatar: Literal['🌱','🚀','🎨','🦊'] = '🌱'
    companion: Literal['Nova','Pip','Atlas'] = 'Nova'

@app.post('/api/v1/learners', status_code=201)
def create_learner(body: LearnerInput, account=Depends(current), session=Depends(db)):
    if body.age != '18+':
        # A production verification provider has not been selected. Never fake consent.
        raise HTTPException(409, 'Child profiles require verified guardian consent. This release is available for adult testing while verification is configured.')
    learner = Learner(account_id=account.id, **body.model_dump())
    session.add(learner)
    session.flush()
    return {'id': learner.id, **body.model_dump()}

@app.get('/api/v1/learners')
def learners(account=Depends(current), session=Depends(db)):
    return [{'id': l.id, 'alias': l.alias, 'age': l.age, 'avatar': l.avatar, 'companion': l.companion} for l in session.scalars(select(Learner).where(Learner.account_id==account.id))]

@app.get('/api/v1/health/live')
def live(): return {'status':'ok'}

@app.get('/api/v1/health/ready')
def ready(session=Depends(db)):
    session.execute(text('SELECT 1'))
    return {'status':'ready', 'ai':'guided'}

from .routes import install_routes
install_routes(app, db, current, owned)
