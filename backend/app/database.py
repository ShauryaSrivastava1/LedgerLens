"""
Database connection and session management.

Uses SQLAlchemy's declarative ORM against PostgreSQL. Connection string
is read from the DATABASE_URL environment variable so the same code works
across local dev, Docker, and production without modification.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://equity_user:equity_pass@localhost:5432/equity_platform",
)

# pool_pre_ping avoids "server closed the connection unexpectedly" errors
# after long idle periods (common with cloud-hosted Postgres).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a DB session and guarantees it's closed
    after the request, even if an exception is raised.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
