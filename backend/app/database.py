import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def build_database(db_path=None):
    path = str(db_path or os.getenv('DB_PATH', './data/fft.db'))
    if path == ':memory:':
        url = 'sqlite://'
    elif path.startswith('sqlite:'):
        url = path
    else:
        Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        url = f'sqlite:///{Path(path).expanduser().resolve()}'
    options = {'connect_args': {'check_same_thread': False, 'timeout': 30}}
    if path == ':memory:' or url in ('sqlite://', 'sqlite:///:memory:'):
        options['poolclass'] = StaticPool
    engine = create_engine(url, **options)

    @event.listens_for(engine, 'connect')
    def sqlite_settings(connection, _):
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA busy_timeout=30000')
        cursor.close()

    return engine, sessionmaker(bind=engine, expire_on_commit=False)
