# ============================================================
# database.py — Database Connection Setup
# This file sets up the async connection to PostgreSQL.
# It creates the engine (connection pool) and a session factory.
# The get_db() function is used as a FastAPI dependency in routes.
# ============================================================
import os
# These are SQLAlchemy async tools for non-blocking database operations:
# create_async_engine  → creates an async connection pool to the database
# async_sessionmaker   → factory that creates new async DB sessions
# AsyncSession         → type hint for a single database session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# The database connection string — tells SQLAlchemy HOW and WHERE to connect.
# Format: dialect+driver://username:password@host/database_name
# postgresql+asyncpg → uses PostgreSQL with the asyncpg async driver
# postgres:postgres  → username:password
# localhost          → the server is running locally
# productcatalog     → name of the database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/knowledgebase")

# Create the async engine — manages the connection pool.
# echo=True means every SQL query will be printed to the terminal (useful for debugging).
# In production you would set echo=False.
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a session factory — each call creates a new database session.
# expire_on_commit=False means ORM objects stay usable after db.commit()
# Without this setting, accessing attributes after commit would raise an error.
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# FastAPI dependency function — automatically injects a DB session into route handlers.
# Using 'async with' ensures the session is properly closed after the request,
# even if an error occurs.
# 'yield' makes this a generator — FastAPI handles setup + teardown automatically.
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session  # The session is injected here into the route function