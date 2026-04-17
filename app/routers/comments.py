from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Comment, Article, User, UserRole, ArticleStatus
from app.schemas import CommentCreate, CommentResponse
from app.dependencies import get_current_user
from app.redis import get_redis
import redis.asyncio as aioredis

router = APIRouter(tags=["comments"])

# ADD COMMENT — authenticated
@router.post("/articles/{slug}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    slug: str,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis)
):
    # Get article
    result = await db.execute(
        select(Article).where(
            Article.slug == slug,
            Article.status == ArticleStatus.PUBLISHED
        )
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Validate parent comment if reply
    if data.parent_id:
        parent_result = await db.execute(
            select(Comment).where(Comment.id == data.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")
        if parent.parent_id is not None:
            raise HTTPException(
                status_code=400,
                detail="Replies to replies are not allowed"
            )

    comment = Comment(
        content=data.content,
        article_id=article.id,
        author_id=current_user.id,
        parent_id=data.parent_id
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    # Invalidate article detail cache
    await redis.delete(f"articles:detail:{slug}")

    return comment

# GET COMMENTS — public
@router.get("/articles/{slug}/comments", response_model=list[CommentResponse])
async def list_comments(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    # Get article
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Get top level comments only
    result = await db.execute(
        select(Comment).where(
            Comment.article_id == article.id,
            Comment.parent_id == None
        )
    )
    return result.scalars().all()

# DELETE COMMENT — author or admin
@router.delete("/articles/{slug}/comments/{comment_id}", status_code=204)
async def delete_comment(
    slug: str,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = await db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    await db.delete(comment)
    await db.commit()