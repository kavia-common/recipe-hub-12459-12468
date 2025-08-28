from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, scoped_session
from sqlalchemy.exc import OperationalError
from typing import Generator

from src.core.config import get_settings


class Base(DeclarativeBase):
    """Base declarative for ORM models."""


def _create_engine_with_fallback(database_url: str):
    """Create an SQLAlchemy engine with fallback to local SQLite if connection fails."""
    connect_args = {}
    # SQLite requires special args to support thread-safe usage in FastAPI
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    try:
        engine = create_engine(database_url, echo=False, future=True, connect_args=connect_args)
        # Try a lightweight connection test
        with engine.connect() as _:
            pass
        return engine
    except OperationalError:
        # Fallback to local SQLite file
        fallback_url = "sqlite:///./data.db"
        engine = create_engine(
            fallback_url, echo=False, future=True, connect_args={"check_same_thread": False}
        )
        return engine


settings = get_settings()
engine = _create_engine_with_fallback(settings.DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


# PUBLIC_INTERFACE
def get_db() -> Generator:
    """Yield a database session and ensure it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
