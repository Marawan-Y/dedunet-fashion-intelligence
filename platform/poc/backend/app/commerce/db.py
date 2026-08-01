"""Database engine, session and declarative base for the commerce domain.

SQLite is the default so a clean checkout can run the full stack with no external
service. The models avoid SQLite-only constructs, so the same schema runs on
PostgreSQL by changing ``DATABASE_URL`` alone.

Two SQLite pragmas matter for correctness and are applied on every connection:

``foreign_keys=ON``
    SQLite ignores foreign keys unless this is set per connection. Without it the
    referential-integrity constraints below would be decorative.

``journal_mode=WAL``
    Allows readers to proceed during a write, which the concurrency tests rely on.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_SQLITE_PATH = os.getenv("COMMERCE_DB_PATH", "commerce.sqlite3")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+pysqlite:///{DEFAULT_SQLITE_PATH}")

_is_sqlite = DATABASE_URL.startswith("sqlite")
_is_memory = _is_sqlite and (":memory:" in DATABASE_URL)

_engine_kwargs: dict[str, object] = {"future": True, "echo": False}
if _is_memory:
    # An in-memory database lives for as long as its connection, so tests must share
    # one connection across sessions or each session would see an empty schema.
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if not _is_memory:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for every commerce table."""


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session that always closes."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_all() -> None:
    """Create the schema directly.

    Used by tests and the local bootstrap. Alembic migrations remain the
    authoritative path for any environment that outlives a single process.
    """

    from . import models  # noqa: F401  (import registers the mappers)

    Base.metadata.create_all(engine)
