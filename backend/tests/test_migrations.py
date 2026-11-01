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


def test_upgrading_keeps_data(tmp_path):
    """Batch mode rebuilds tables on SQLite; with foreign keys on, that used to be able to cascade-delete."""
    url = f"sqlite:///{(tmp_path / 'data.db').as_posix()}"
    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "4530e0aa1d0c")  # before users.auth_subject became nullable

    engine = make_engine(url)
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO users (id, auth_subject, email, display_name) VALUES (1, 's', 'a@x', 'A')")
        conn.exec_driver_sql("INSERT INTO households (id, name) VALUES (1, 'Home')")
        conn.exec_driver_sql(
            "INSERT INTO memberships (household_id, user_id, role, split_weight) VALUES (1, 1, 'owner', 1)"
        )
        conn.exec_driver_sql("INSERT INTO accounts (id, owner_id, name, currency) VALUES (1, 1, 'Amex', 'SEK')")
        conn.exec_driver_sql(
            "INSERT INTO transactions (account_id, booked_on, description_raw, description_clean, amount_minor,"
            " currency, allocation) VALUES (1, '2025-07-01', 'x', 'x', 100, 'SEK', 'shared')"
        )
    command.upgrade(config, "head")
    with engine.connect() as conn:
        counts = [conn.exec_driver_sql(f"SELECT count(*) FROM {t}").scalar() for t in ("memberships", "accounts", "transactions")]
    engine.dispose()
    assert counts == [1, 1, 1]
