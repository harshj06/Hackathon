from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from cognify.models import Base, SchemaVersion
from cognify.config import ROOT

def make_engine(url):
    if url.startswith('sqlite:///') and url != 'sqlite:///:memory:':
        path = Path(url.removeprefix('sqlite:///'))
        if not path.is_absolute():
            path = ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        url = 'sqlite:///' + str(path)
    opts = {'connect_args': {'check_same_thread': False, 'timeout': 20}} if url.startswith('sqlite') else {}
    if url == 'sqlite:///:memory:':
        opts['poolclass'] = StaticPool
    engine = create_engine(url, **opts)
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def sqlite_settings(conn, record):
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA journal_mode=WAL')
    return engine

def initialize(engine):
    Base.metadata.create_all(engine)
    for table in Base.metadata.sorted_tables:
        for index in table.indexes:
            index.create(engine,checkfirst=True)
    from cognify.catalog import seed_catalog
    with sessionmaker(engine).begin() as session:
        seed_catalog(session)
        if not session.get(SchemaVersion,2):
            session.add(SchemaVersion(version=2))

def session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)

if __name__ == '__main__':
    from cognify.config import Settings
    initialize(make_engine(Settings.load().database_url))
    print('Database initialized.')
