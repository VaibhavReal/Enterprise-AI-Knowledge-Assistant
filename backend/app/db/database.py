"""
Database engine, session factory, and Base for SQLAlchemy models.

We use PostgreSQL with the psycopg2 driver. The pgvector extension must be
enabled before creating tables (handled in create_tables()).
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import get_settings
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

settings = get_settings()

# pool_pre_ping=True sends a lightweight test query before using a connection.
# This prevents errors when the database connection has been closed due to timeout.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Session factory — autocommit=False means we explicitly commit or rollback
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All SQLAlchemy models inherit from this Base
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a database session per request.

    The try/finally ensures the session is always closed after the request,
    even if an exception occurs during request handling. This prevents
    connection pool exhaustion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Enable the pgvector extension and create all database tables.

    Called once at application startup (in main.py lifespan).
    Idempotent: safe to call even if tables already exist.
    """
    try:
        if "postgresql" in settings.DATABASE_URL:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
                logger.info("pgvector extension enabled")
    except Exception as e:
        logger.warning(f"Could not enable pgvector extension (may already exist or running SQLite): {e}")

    try:
        # Import models here to ensure they are registered with Base.metadata
        import app.db.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
