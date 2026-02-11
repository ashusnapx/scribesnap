"""
Alembic Migration Environment
===============================

What:  Configures Alembic to work with our async SQLAlchemy setup.
Why:   Alembic needs to know how to connect to the database and which
       models to track for auto-generating migrations.
How:   Overrides default sync Alembic with async engine from our config.
Who:   Called by `alembic` CLI commands (upgrade, downgrade, revision).
When:  During migration operations (development and deployment).
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.config import settings
from app.database import Base

# Import all models so Alembic can detect them for --autogenerate
# Why: Alembic only sees models that are imported and registered with Base
from app.models.note import Note  # noqa: F401

# Alembic Config object — provides access to .ini file values
config = context.config

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# What: Tell Alembic about our model metadata
# Why: Enables --autogenerate to detect schema changes automatically
target_metadata = Base.metadata

# Override database URL from our settings (not from alembic.ini)
# Why: Single source of truth for database configuration
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    What:  Generates SQL migration scripts without connecting to the database.
    When:  Useful for reviewing SQL before applying, or when DB is unreachable.
    How:   Uses the URL directly to emit SQL to stdout.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """
    Execute migrations against the provided connection.
    
    What:  Runs the actual migration steps in a transaction.
    Why separate: Shared between online sync and async paths.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.
    
    What:  Connects to the database and applies pending migrations.
    Why async: Our app uses async SQLAlchemy; Alembic needs an async engine.
    How:   Creates an async engine, runs migrations in a sync context via
           connection.run_sync().
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't use pooling for migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — bridges async engine with Alembic."""
    asyncio.run(run_async_migrations())


# Determine which mode to run in
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
