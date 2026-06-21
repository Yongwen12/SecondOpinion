from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def require_sqlalchemy():
    try:
        import sqlalchemy  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only in missing optional dependency environments.
        raise RuntimeError(
            "SecondOpinion server dependencies are not installed. "
            "Install the project with the server extras or install fastapi/sqlalchemy/alembic."
        ) from exc


require_sqlalchemy()

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker  # noqa: E402


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    db_path = Path(database_url.replace("sqlite:///", "", 1))
    if db_path != Path(":memory:"):
        db_path.parent.mkdir(parents=True, exist_ok=True)


def make_engine(database_url: str) -> Engine:
    _ensure_sqlite_parent(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db(engine: Engine) -> None:
    from . import models  # noqa: F401 - registers models on Base.metadata

    Base.metadata.create_all(engine)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

