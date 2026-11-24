"""
One-off local-dev convenience script: creates all tables against
DATABASE_URL. Run with `python -m app.init_db`.

Do NOT use this in production — use Alembic migrations
(see /alembic) so schema changes are versioned and reversible.
"""

from app.database import Base, engine
from app import models  # noqa: F401  (import registers models on Base.metadata)


def main():
    Base.metadata.create_all(bind=engine)
    print("Tables created.")


if __name__ == "__main__":
    main()
