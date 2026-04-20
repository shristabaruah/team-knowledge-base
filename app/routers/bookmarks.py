from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Bookmark, Article, User, ArticleStatus
from app.schemas import BookmarkResponse
from app.dependencies import get_current_user

router = APIRouter(tags=["bookmarks"])

# TOGGLE BOOKMARK — authenticated
@router.post("/articles/{slug}/bookmark")
async def toggle_bookmark(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Article).where(
            Article.slug == slug,
            Article.status == ArticleStatus.PUBLISHED
        )
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    result = await db.execute(
        select(Bookmark).where(
            Bookmark.user_id == current_user.id,
            Bookmark.article_id == article.id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        await db.delete(existing)
        await db.commit()
        return {"bookmarked": False, "message": "Bookmark removed"}
    else:
        bookmark = Bookmark(
            user_id=current_user.id,
            article_id=article.id
        )
        db.add(bookmark)
        await db.commit()
        return {"bookmarked": True, "message": "Bookmark added"}

# GET MY BOOKMARKS — authenticated
@router.get("/bookmarks/my", response_model=list[BookmarkResponse])
async def my_bookmarks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Bookmark)
        .options(
            selectinload(Bookmark.article)
            .selectinload(Article.tags),
            selectinload(Bookmark.article)
            .selectinload(Article.author)
        )
        .where(Bookmark.user_id == current_user.id)
    )
    return result.scalars().all()