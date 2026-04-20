import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import redis.asyncio as aioredis
from app.routers import auth, articles, tags, comments, bookmarks, admin
from app.database import get_db
from app.redis import get_redis
from app.config import settings

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Team Knowledge Base API",
    description="A shared knowledge base API for teams",
    version="1.0.0"
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(articles.router)
app.include_router(tags.router)
app.include_router(comments.router)
app.include_router(bookmarks.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Team Knowledge Base API!"}

# Health check
@app.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
        logger.info("Database health check passed")
    except Exception as e:
        db_status = "unhealthy"
        logger.error(f"Database health check failed: {e}")

    try:
        await redis.ping()
        redis_status = "healthy"
        logger.info("Redis health check passed")
    except Exception as e:
        redis_status = "unhealthy"
        logger.error(f"Redis health check failed: {e}")

    return {
        "status": "healthy",
        "database": db_status,
        "redis": redis_status
    }