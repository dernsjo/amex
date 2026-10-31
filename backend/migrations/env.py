from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from app import models  # noqa: F401  registers tables on Base.metadata
from app.database import Base, make_engine
from app.settings import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
url = config.get_main_option("sqlalchemy.url") or settings.database_url
# SQLite can't ALTER most things in place; batch mode recreates tables instead.
render_as_batch = url.startswith("sqlite")


def run_migrations_offline() -> None:
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, render_as_batch=render_as_batch)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = make_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=render_as_batch)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
