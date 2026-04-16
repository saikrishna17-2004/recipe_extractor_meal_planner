from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine_kwargs = {'future': True, 'pool_pre_ping': True}
database_url = settings.normalized_database_url

if os.getenv('RENDER') and database_url.startswith('sqlite'):
    raise RuntimeError('DATABASE_URL is not configured on Render. Configure your managed Postgres connection string.')

if database_url.startswith('sqlite'):
    engine_kwargs['connect_args'] = {'check_same_thread': False}

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
