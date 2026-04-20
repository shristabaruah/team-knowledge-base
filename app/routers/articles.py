import json
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from app.database import get_db
from app.models import Article, Tag, User, ArticleStatus
from app.schemas import ArticleCreate, ArticleUpdate, ArticleResponse
from app.dependencies import get_current_user
from app.redis import get_redis
import redis.asyncio as aioredis
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/articles", tags=["articles"])

# Helper — generate slug from title
def generate_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    return slug.strip('-')

# Helper — get or create tags
async def get_or_create_tags(tag_names: list[str], db: AsyncSession) -> list[Tag]:
    tags = []
    for name in tag_names:
        name = name.lower().strip()
        result = await db.execute(select(Tag).where(Tag.name == name))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(name=name, slug=generate_slug(name))
            db.add(tag)
            await db.flush()
        tags.append(tag)
    return tags

# GET ALL PUBLISHED ARTICLES — public, cached
@router.get("/", response_model=list[ArticleResponse])
async def list_articles(
    skip: int = 0,
    limit: int = 10,
    tag: str = None,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    cache_key = f"articles:list:skip:{skip}:limit:{limit}:tag:{tag}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    query = select(Article)\
        .options(selectinload(Article.tags), selectinload(Article.author))\
        .where(Article.status == ArticleStatus.PUBLISHED)
    if tag:
        query = query.join(Article.tags).where(Tag.slug == tag)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    articles = result.scalars().all()

    articles_data = [ArticleResponse.model_validate(a).model_dump(mode="json") for a in articles]
    await redis.set(cache_key, json.dumps(articles_data), ex=300)

    return articles

# GET MY DRAFTS — authenticated
@router.get("/my/drafts", response_model=list[ArticleResponse])
async def my_drafts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.author))
        .where(
            Article.author_id == current_user.id,
            Article.status == ArticleStatus.DRAFT
        )
    )
    return result.scalars().all()

# GET ONE ARTICLE BY SLUG — public, cached
@router.get("/{slug}", response_model=ArticleResponse)
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    cache_key = f"articles:detail:{slug}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.author))
        .where(
            Article.slug == slug,
            Article.status == ArticleStatus.PUBLISHED
        )
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Increment view count
    article.view_count += 1
    await db.commit()

    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.author))
        .where(Article.id == article.id)
    )
    article = result.scalar_one()

    article_data = ArticleResponse.model_validate(article).model_dump(mode="json")
    await redis.set(cache_key, json.dumps(article_data), ex=600)

    return article

# CREATE ARTICLE — authenticated
@router.post("/", response_model=ArticleResponse, status_code=201)
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis)
):
    # Generate unique slug
    base_slug = generate_slug(data.title)
    slug = base_slug
    counter = 1
    while True:
        result = await db.execute(select(Article).where(Article.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Get or create tags
    tags = await get_or_create_tags(data.tags, db)

    article = Article(
        title=data.title,
        slug=slug,
        content=data.content,
        summary=data.summary,
        status=data.status,
        author_id=current_user.id,
        published_at=datetime.utcnow() if data.status == ArticleStatus.PUBLISHED else None
    )
    article.tags = tags
    db.add(article)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.author))
        .where(Article.id == article.id)
    )
    article = result.scalar_one()

    # Invalidate cache
    await invalidate_article_cache(redis)

    return article

# UPDATE ARTICLE — author or admin
@router.patch("/{slug}", response_model=ArticleResponse)
async def update_article(
    slug: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis)
):
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.author))
        .where(Article.slug == slug)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    from app.models import UserRole
    if article.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Set published_at when first published
    if data.status == ArticleStatus.PUBLISHED and article.published_at is None:
        article.published_at = datetime.utcnow()

    # Update tags if provided
    if data.tags is not None:
        article.tags = await get_or_create_tags(data.tags, db)

    for key, value in data.model_dump(exclude_unset=True, exclude={"tags"}).items():
        setattr(article, key, value)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.author))
        .where(Article.slug == slug)
    )
    article = result.scalar_one()

    # Invalidate cache
    await invalidate_article_cache(redis)
    await redis.delete(f"articles:detail:{slug}")

    return article

# DELETE ARTICLE — author or admin (soft delete)
@router.delete("/{slug}", status_code=204)
async def delete_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis)
):
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    from app.models import UserRole
    if article.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Soft delete
    article.status = ArticleStatus.ARCHIVED
    await db.commit()

    # Invalidate cache
    await invalidate_article_cache(redis)
    await redis.delete(f"articles:detail:{slug}")

# Helper — invalidate all article list caches
async def invalidate_article_cache(redis: aioredis.Redis):
    keys = await redis.keys("articles:list:*")
    if keys:
        await redis.delete(*keys)