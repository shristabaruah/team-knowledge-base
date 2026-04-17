from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from app.models import UserRole, ArticleStatus

# ---- User Schemas ----

class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: UserRole
    bio: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None

# ---- Token Schemas ----

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# ---- Tag Schemas ----

class TagResponse(BaseModel):
    id: int
    name: str
    slug: str

    model_config = {"from_attributes": True}

class TagCreate(BaseModel):
    name: str

# ---- Article Schemas ----

class ArticleCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    status: ArticleStatus = ArticleStatus.DRAFT
    tags: list[str] = []  # list of tag names

class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[ArticleStatus] = None
    tags: Optional[list[str]] = None

class ArticleResponse(BaseModel):
    id: int
    title: str
    slug: str
    content: str
    summary: Optional[str]
    status: ArticleStatus
    is_featured: bool
    view_count: int
    published_at: Optional[datetime]
    created_at: datetime
    author: UserResponse
    tags: list[TagResponse] = []

    model_config = {"from_attributes": True}

# ---- Comment Schemas ----

class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None

class CommentResponse(BaseModel):
    id: int
    content: str
    author: UserResponse
    parent_id: Optional[int]
    created_at: datetime
    replies: list["CommentResponse"] = []

    model_config = {"from_attributes": True}

# ---- Bookmark Schemas ----

class BookmarkResponse(BaseModel):
    id: int
    article: ArticleResponse
    created_at: datetime

    model_config = {"from_attributes": True}

# ---- Admin Schemas ----

class RoleUpdate(BaseModel):
    role: UserRole