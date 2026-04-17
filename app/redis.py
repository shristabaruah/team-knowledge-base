# ============================================================
# redis.py — Redis Connection Setup
# Redis is an in-memory key-value store used for caching.
# Instead of hitting the database on every request, we store
# frequently-read data in Redis for ultra-fast retrieval.
# This file provides the get_redis() FastAPI dependency.
# ============================================================

# redis.asyncio is the async version of the redis-py client.
# We import it as 'aioredis' as a shorthand alias.
import redis.asyncio as aioredis
import os

# The Redis connection URL.
# redis://     → protocol
# localhost    → Redis is running on the same machine
# 6379         → default Redis port
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")



# FastAPI dependency — creates and yields a Redis client for each request.
# Using 'yield' ensures the connection is properly closed after the request ends,
# even if an error occurs (similar to how get_db() works for PostgreSQL).
async def get_redis():
    # Create a Redis client connected to our local Redis server.
    # decode_responses=True → automatically converts byte responses to Python strings
    # (Without this, Redis returns bytes like b"hello" instead of "hello")
    client = aioredis.from_url(REDIS_URL, decode_responses=True)

    try:
        yield client   # Inject the client into the route that depends on this
    finally:
        await client.aclose()  # Always close the connection when done