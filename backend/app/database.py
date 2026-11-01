from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .settings import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str, **kwargs):
    if not url.startswith("sqlite"):
        return create_engine(url, **kwargs)
    engine = create_engine(url, connect_args={"check_same_thread": False}, **kwargs)

    # SQLite ignores foreign keys (and so ON DELETE CASCADE) unless asked, per connection.
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
