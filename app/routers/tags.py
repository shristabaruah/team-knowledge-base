import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Tag, Article, ArticleStatus
from app.schemas import TagCreate, TagResponse
from app.dependencies import require_admin
from app.redis import get_redis
import redis.asyncio as aioredis
import re

router = APIRouter(prefix="/tags", tags=["tags"])

# Helper — generate slug
def generate_slug(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    return slug.strip('-')

# GET ALL TAGS — public, cached
@router.get("/", response_model=list[TagResponse])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    cache_key = "tags:all"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await db.execute(select(Tag))
    tags = result.scalars().all()

    tags_data = [TagResponse.model_validate(t).model_dump(mode="json") for t in tags]
    await redis.set(cache_key, json.dumps(tags_data), ex=900)  # 15 min TTL

    return tags

# CREATE TAG — admin only
@router.post("/", response_model=TagResponse, status_code=201)
async def create_tag(
    data: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
    redis: aioredis.Redis = Depends(get_redis)
):
    name = data.name.lower().strip()
    result = await db.execute(select(Tag).where(Tag.name == name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag = Tag(name=name, slug=generate_slug(name))
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    # Invalidate cache
    await redis.delete("tags:all")

    return tag

# GET ARTICLES BY TAG — public, cached
@router.get("/{slug}/articles")
async def articles_by_tag(
    slug: str,
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    cache_key = f"tags:{slug}:articles:skip:{skip}:limit:{limit}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Check tag exists
    result = await db.execute(select(Tag).where(Tag.slug == slug))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Get published articles with this tag
    result = await db.execute(
        select(Article)
        .join(Article.tags)
        .where(Tag.slug == slug)
        .where(Article.status == ArticleStatus.PUBLISHED)
        .offset(skip)
        .limit(limit)
    )
    articles = result.scalars().all()

    from app.schemas import ArticleResponse
    articles_data = [ArticleResponse.model_validate(a).model_dump(mode="json") for a in articles]
    await redis.set(cache_key, json.dumps(articles_data), ex=900)

    return articles_data