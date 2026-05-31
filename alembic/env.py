import asyncio
import os
import sys

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# --------------------------------------------------
# FIX PYTHON PATH
# --------------------------------------------------

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

# --------------------------------------------------
# IMPORT APP
# --------------------------------------------------

from app.db.base import Base
import app.models

# --------------------------------------------------
# ALEMBIC CONFIG
# --------------------------------------------------

config = context.config

# --------------------------------------------------
# DATABASE URL
# --------------------------------------------------

DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/socialpulse"

config.set_main_option("sqlalchemy.url", DATABASE_URL)

# --------------------------------------------------
# LOGGING
# --------------------------------------------------

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --------------------------------------------------
# METADATA
# --------------------------------------------------

target_metadata = Base.metadata

# --------------------------------------------------
# OFFLINE MIGRATIONS
# --------------------------------------------------

def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# --------------------------------------------------
# ONLINE MIGRATIONS
# --------------------------------------------------

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

# --------------------------------------------------
# ENTRY
# --------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()