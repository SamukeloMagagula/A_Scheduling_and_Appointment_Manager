"""SQLAlchemy engine + scoped session. One connection pool for the app."""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker

from config import Config


class Base(DeclarativeBase):
    pass


engine = create_engine(
    Config.SQLALCHEMY_URL,
    pool_pre_ping=True,     # drop dead connections instead of erroring the next request
    pool_recycle=1800,      # recycle every 30 min so MariaDB's wait_timeout can't kill us mid-request
    future=True,
)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
)


@contextmanager
def session_scope():
    """Short-lived unit of work. Commits on success, rolls back on error."""
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
