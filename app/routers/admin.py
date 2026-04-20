from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import User, Article
from app.schemas import UserResponse, RoleUpdate, ArticleResponse
from app.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

# GET ALL USERS — admin only
@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin)
):
    result = await db.execute(select(User))
    return result.scalars().all()

# CHANGE USER ROLE — admin only
@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def change_role(
    user_id: int,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = data.role
    await db.commit()
    await db.refresh(user)
    return user

# TOGGLE FEATURED ARTICLE — admin only
@router.patch("/articles/{slug}/feature", response_model=ArticleResponse)
async def toggle_feature(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin)
):
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.author))
        .where(Article.slug == slug)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Toggle featured status
    article.is_featured = not article.is_featured
    await db.commit()
    await db.refresh(article)

    # Reload with relationships
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.tags), selectinload(Article.author))
        .where(Article.slug == slug)
    )
    article = result.scalar_one()

    return article