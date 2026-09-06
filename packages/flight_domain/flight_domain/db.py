import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from flight_domain.config import settings

def get_engine_url(raw_url: str) -> str:
    # Convert postgres:// or postgresql:// to postgresql+psycopg:// if needed
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_url

def create_db_engine(db_url: str | None = None):
    url = get_engine_url(db_url or settings.DATABASE_URL)
    connect_args = {}
    
    if "postgresql" in url:
        # If using transaction pooler or session pooler, setting prepare_threshold=None
        # in psycopg avoids "prepared statement does not exist" errors.
        connect_args["prepare_threshold"] = None
    elif "sqlite" in url:
        connect_args["check_same_thread"] = False

    engine = create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    return engine

engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
