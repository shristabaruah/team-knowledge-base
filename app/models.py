from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, Enum, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
import enum

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"

class ArticleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class Base(DeclarativeBase):
    pass

# Association table for Article <-> Tag (many-to-many)
from sqlalchemy import Table, Column
article_tags = Table(
    "article_tags",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.MEMBER)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    articles: Mapped[list["Article"]] = relationship(back_populates="author")
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="user")

class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(String(280), nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ArticleStatus] = mapped_column(Enum(ArticleStatus), default=ArticleStatus.DRAFT)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    author: Mapped["User"] = relationship(back_populates="articles")
    tags: Mapped[list["Tag"]] = relationship(secondary=article_tags, back_populates="articles")
    comments: Mapped[list["Comment"]] = relationship(back_populates="article")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="article")

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)

    articles: Mapped[list["Article"]] = relationship(secondary=article_tags, back_populates="tags")

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("comments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    article: Mapped["Article"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")
    replies: Mapped[list["Comment"]] = relationship(back_populates="parent")
    parent: Mapped[Optional["Comment"]] = relationship(back_populates="replies", remote_side="Comment.id")

class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="bookmarks")
    article: Mapped["Article"] = relationship(back_populates="bookmarks")