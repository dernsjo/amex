from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from app.database import Base, make_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_migrations_match_models(tmp_path):
    """Fails if a model changed without a migration (run `alembic revision --autogenerate`)."""
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    engine = make_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == []

    command.downgrade(config, "base")
