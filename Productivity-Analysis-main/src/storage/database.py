"""Database engine initialization, connection pooling, and session management.

Supports both SQLite (for zero-setup standalone edge deployment) and
PostgreSQL/TimescaleDB (for enterprise production cluster deployments).
"""

from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from src.core.config import settings
from src.core.logging import logger

# SQLite specific connect arguments for thread safety
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Enable WAL mode for SQLite to prevent write-lock deadlocks
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency generator for FastAPI endpoints providing database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Creates database tables if they do not already exist."""
    import src.storage.models  # Ensure models are imported
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized successfully.")
