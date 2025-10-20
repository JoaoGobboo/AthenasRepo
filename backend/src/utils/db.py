from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = None
SessionLocal = None


def init_engine(database_uri: str) -> None:
    global engine, SessionLocal
    if engine:
        return
    connect_args = {}
    if database_uri.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    engine = create_engine(
        database_uri, pool_pre_ping=True, future=True, connect_args=connect_args
    )
    SessionLocal = scoped_session(
        sessionmaker(bind=engine, autoflush=False, autocommit=False)
    )


def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database engine is not initialized")
    return SessionLocal()


def remove_session() -> None:
    if SessionLocal is not None:
        SessionLocal.remove()


def get_engine():
    if engine is None:
        raise RuntimeError("Database engine is not initialized")
    return engine


@contextmanager
def session_scope() -> Generator:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
