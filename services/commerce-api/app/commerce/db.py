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

from datetime import datetime, timezone

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

if not _is_sqlite:
    # A networked database drops idle connections: container restarts, proxy idle
    # timeouts, failovers. Without pre-ping the first request after such a drop fails
    # with a stale-connection OperationalError - the classic "works, then 500s after
    # lunch". pre_ping costs one cheap round trip and removes that whole failure class.
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_recycle"] = 1800
    # The concurrency test runs 20 simultaneous reservations; the default pool of
    # 5 + 10 overflow would make five of them queue on checkout rather than exercise
    # the database-level guard the test exists to prove.
    _engine_kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "10"))
    _engine_kwargs["max_overflow"] = int(os.getenv("DB_MAX_OVERFLOW", "20"))

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


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """Normalise a timestamp read back from the database to an aware UTC value.

    SQLite has no timestamp type: it ignores ``DateTime(timezone=True)`` and returns a
    NAIVE datetime. PostgreSQL stores TIMESTAMPTZ and returns an AWARE one. The same
    row therefore serialises differently depending on the engine, and comparing or
    subtracting two such values raises ``TypeError: can't subtract offset-naive and
    offset-aware datetimes`` on one backend while silently working on the other.

    Writes are already safe because ``utcnow()`` produces aware values. This closes the
    read side so one wire format and one comparison semantics hold on both engines.

    A naive value is ASSUMED to be UTC, which is true here because every write goes
    through ``utcnow()``. It is not a safe assumption for arbitrary external input.

    LIVES HERE, not in models.py, so that every mapped module can import it without
    importing the models module -- which is what let `brands.py` become a peer of
    `models.py` instead of a cycle.
    """

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
