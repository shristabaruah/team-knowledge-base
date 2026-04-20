# ============================================================
# alembic/env.py — Alembic Migration Environment
# Alembic uses this file every time you run a migration command
# (e.g. alembic revision --autogenerate OR alembic upgrade head).
# It tells Alembic: how to connect to the DB, and what tables to compare.
# This version is configured for ASYNC SQLAlchemy (asyncpg driver).
# ============================================================

# asyncio → Python's standard library for running async code
import asyncio

# fileConfig → reads the logging configuration from alembic.ini
from logging.config import fileConfig

# create_async_engine → same as in database.py, creates an async DB connection
from sqlalchemy.ext.asyncio import create_async_engine

# context → Alembic's object for controlling migration execution
from alembic import context

# Base → our ORM base class; its .metadata knows about all our tables (User, Product)
from app.models import Base

# Import the DB URL from our database.py (single source of truth)
from app.database import DATABASE_URL


# ---- Alembic Config Setup ----

# context.config gives access to the alembic.ini file settings
config = context.config

# Set up Python logging using the [loggers] section of alembic.ini
fileConfig(config.config_file_name)

# This is what Alembic compares against the actual database to detect changes.
# It looks at all tables defined in our SQLAlchemy models (User, Product, etc.)
target_metadata = Base.metadata


# ============================================================
# run_migrations_offline()
# Used when you run: alembic upgrade head --sql (generates SQL script only)
# Does NOT connect to the database — just generates migration SQL statements.
# ============================================================
def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,                       # The DB connection string
        target_metadata=target_metadata,        # Our model definitions
        literal_binds=True,                     # Use literal values in SQL (not placeholders)
        dialect_opts={"paramstyle": "named"},   # Use named parameters (:name) style
    )
    with context.begin_transaction():
        context.run_migrations()  # Generate and output the SQL


# ============================================================
# do_run_migrations(connection)
# A helper function that configures the context with a live DB connection
# and actually executes the migration SQL against the database.
# Called by run_migrations_online() after the connection is established.
# ============================================================
def do_run_migrations(connection):
    context.configure(
        connection=connection,          # Live async DB connection
        target_metadata=target_metadata # Our model definitions to compare
    )
    with context.begin_transaction():
        context.run_migrations()  # Execute the actual SQL migration


# ============================================================
# run_migrations_online()
# The standard migration mode — connects to the database and applies changes.
# Used when you run: alembic upgrade head OR alembic revision --autogenerate
# Because we use asyncpg (async driver), we need asyncio.run() to drive the async code.
# ============================================================
async def run_migrations_online():
    # Create a temporary async engine just for running migrations
    connectable = create_async_engine(DATABASE_URL)

    # Open an async connection to the database
    async with connectable.connect() as connection:
        # run_sync() bridges the gap: Alembic's migration runner is synchronous,
        # but our connection is async. run_sync() runs sync code inside an async context.
        await connection.run_sync(do_run_migrations)

    # Release all connections back to the pool when done
    await connectable.dispose()


# ============================================================
# Entry Point — decides which mode to run
# ============================================================

if context.is_offline_mode():
    # Offline mode: just generate SQL without connecting to DB
    run_migrations_offline()
else:
    # Online mode: connect to DB and run migrations
    # asyncio.run() starts the event loop to execute our async function
    asyncio.run(run_migrations_online())