import pytest
from cognify.db import make_engine, initialize, session_factory
from cognify.services.accounts import register, create_profile, ProfileInput

@pytest.fixture
def factory():
    engine = make_engine('sqlite:///:memory:')
    initialize(engine)
    yield session_factory(engine)
    engine.dispose()

@pytest.fixture
def learner(factory):
    with factory.begin() as s:
        u = register(s,'learner_one','a-long-password','learner')
        p = create_profile(s,u.id,ProfileInput(nickname='N',age_group='18–24',education='University',
            interests=['Space'],subjects=['Mathematics','Computing'],goals='Build understanding',preference='Visual'))
    return u,p
