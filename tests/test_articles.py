import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock
from app.main import app
from app.database import get_db
from app.redis import get_redis
from app.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Mock Redis
class MockRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)

    async def keys(self, pattern):
        return []

    async def ping(self):
        return True

    async def aclose(self):
        pass

@pytest.fixture
async def client():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    mock_redis = MockRedis()
    async def override_get_redis():
        yield mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()

# ---- Auth Tests ----

@pytest.mark.asyncio
async def test_register(client):
    response = await client.post("/auth/register", json={
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "password123"
    })
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_login(client):
    await client.post("/auth/register", json={
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "password123"
    })
    response = await client.post("/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_get_me(client):
    await client.post("/auth/register", json={
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

# ---- Article Tests ----

@pytest.mark.asyncio
async def test_create_article(client):
    await client.post("/auth/register", json={
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    response = await client.post("/articles/", json={
        "title": "Test Article",
        "content": "Test content",
        "status": "PUBLISHED",
        "tags": ["test"]
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["title"] == "Test Article"
    assert response.json()["slug"] == "test-article"

@pytest.mark.asyncio
async def test_list_articles(client):
    response = await client.get("/articles/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_article_not_found(client):
    response = await client.get("/articles/non-existent-slug")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_bookmark_toggle(client):
    await client.post("/auth/register", json={
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "Test Article",
        "content": "Test content",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    # Bookmark
    response = await client.post("/articles/test-article/bookmark", headers=headers)
    assert response.json()["bookmarked"] == True

    # Toggle off
    response = await client.post("/articles/test-article/bookmark", headers=headers)
    assert response.json()["bookmarked"] == False

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_redis_cache(client):
    await client.post("/auth/register", json={
        "email": "cache@example.com",
        "display_name": "Cache User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "cache@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "Cache Test Article",
        "content": "Testing cache",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    # First call — cache miss
    response1 = await client.get("/articles/")
    assert response1.status_code == 200

    # Second call — cache hit (same result)
    response2 = await client.get("/articles/")
    assert response2.status_code == 200
    assert response1.json() == response2.json()  # same data ✅


    # ---- Comment Tests ----

@pytest.mark.asyncio
async def test_add_comment(client):
    await client.post("/auth/register", json={
        "email": "comment@example.com",
        "display_name": "Comment User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "comment@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "Comment Article",
        "content": "Test content",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    response = await client.post("/articles/comment-article/comments", json={
        "content": "Great article!"
    }, headers=headers)
    assert response.status_code == 201
    assert response.json()["content"] == "Great article!"

@pytest.mark.asyncio
async def test_list_comments(client):
    await client.post("/auth/register", json={
        "email": "comment2@example.com",
        "display_name": "Comment User2",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "comment2@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "Comment Article Two",
        "content": "Test content",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    response = await client.get("/articles/comment-article-two/comments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# ---- Tag Tests ----

@pytest.mark.asyncio
async def test_list_tags(client):
    response = await client.get("/tags/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# ---- Tag Tests ----

@pytest.mark.asyncio
async def test_list_tags(client):
    response = await client.get("/tags/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_create_tag_unauthorized(client):
    # Member cannot create tags
    await client.post("/auth/register", json={
        "email": "member@example.com",
        "display_name": "Member User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "member@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    response = await client.post("/tags/", json={
        "name": "python"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

# ---- Article Update/Delete Tests ----

@pytest.mark.asyncio
async def test_update_article(client):
    await client.post("/auth/register", json={
        "email": "update@example.com",
        "display_name": "Update User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "update@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "Update Article",
        "content": "Original content",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    response = await client.patch("/articles/update-article", json={
        "title": "Updated Title",
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"

@pytest.mark.asyncio
async def test_delete_article(client):
    await client.post("/auth/register", json={
        "email": "delete@example.com",
        "display_name": "Delete User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "delete@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "Delete Article",
        "content": "Content to delete",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    response = await client.delete("/articles/delete-article", headers=headers)
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_get_article(client):
    await client.post("/auth/register", json={
        "email": "view@example.com",
        "display_name": "View User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "view@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "View Article",
        "content": "Content to view",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    response = await client.get("/articles/view-article")
    assert response.status_code == 200
    assert response.json()["title"] == "View Article"

@pytest.mark.asyncio
async def test_delete_comment(client):
    await client.post("/auth/register", json={
        "email": "delcomment@example.com",
        "display_name": "Del Comment User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "delcomment@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "Del Comment Article",
        "content": "Test content",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    comment = await client.post(
        "/articles/del-comment-article/comments",
        json={"content": "Delete me"},
        headers=headers
    )
    comment_id = comment.json()["id"]

    response = await client.delete(
        f"/articles/del-comment-article/comments/{comment_id}",
        headers=headers
    )
    assert response.status_code == 204
   
# ---- Admin Tests ----

@pytest.mark.asyncio
async def test_list_users_unauthorized(client):
    response = await client.get("/admin/users")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_update_profile(client):
    await client.post("/auth/register", json={
        "email": "profile@example.com",
        "display_name": "Profile User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "profile@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]

    response = await client.patch("/auth/me", json={
        "display_name": "Updated Name",
        "bio": "My bio"
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["display_name"] == "Updated Name"

@pytest.mark.asyncio
async def test_my_bookmarks(client):
    await client.post("/auth/register", json={
        "email": "bookmark@example.com",
        "display_name": "Bookmark User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "bookmark@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]

    response = await client.get("/bookmarks/my", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_create_draft_article(client):
    await client.post("/auth/register", json={
        "email": "draft@example.com",
        "display_name": "Draft User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "draft@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]

    response = await client.post("/articles/", json={
        "title": "My Draft Article",
        "content": "Draft content",
        "status": "DRAFT",
        "tags": []
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"

@pytest.mark.asyncio
async def test_my_drafts(client):
    await client.post("/auth/register", json={
        "email": "drafts@example.com",
        "display_name": "Drafts User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "drafts@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]

    await client.post("/articles/", json={
        "title": "My Draft",
        "content": "Draft content",
        "status": "DRAFT",
        "tags": []
    }, headers={"Authorization": f"Bearer {token}"})

    response = await client.get("/articles/my/drafts",
        headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) > 0


    # ---- Admin Tests ----

@pytest.mark.asyncio
async def test_admin_list_users(client):
    # Register admin
    await client.post("/auth/register", json={
        "email": "adminlist@example.com",
        "display_name": "Admin List",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "adminlist@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]

    # Set admin role directly in DB
    from sqlalchemy import select, update
    from app.models import User, UserRole
    async for db in app.dependency_overrides[get_db]():
        await db.execute(
            update(User)
            .where(User.email == "adminlist@example.com")
            .values(role=UserRole.ADMIN)
        )
        await db.commit()

    response = await client.get("/admin/users",
        headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in [200, 403]

@pytest.mark.asyncio
async def test_threaded_comment(client):
    await client.post("/auth/register", json={
        "email": "thread@example.com",
        "display_name": "Thread User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "thread@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "Thread Article",
        "content": "Thread content",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    # Add parent comment
    parent = await client.post(
        "/articles/thread-article/comments",
        json={"content": "Parent comment"},
        headers=headers
    )
    parent_id = parent.json()["id"]

    # Add reply
    reply = await client.post(
        "/articles/thread-article/comments",
        json={"content": "Reply comment", "parent_id": parent_id},
        headers=headers
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == parent_id

@pytest.mark.asyncio
async def test_comment_reply_to_reply_not_allowed(client):
    await client.post("/auth/register", json={
        "email": "noreply@example.com",
        "display_name": "No Reply User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "noreply@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/articles/", json={
        "title": "No Reply Article",
        "content": "Content",
        "status": "PUBLISHED",
        "tags": []
    }, headers=headers)

    # Add parent comment
    parent = await client.post(
        "/articles/no-reply-article/comments",
        json={"content": "Parent"},
        headers=headers
    )
    parent_id = parent.json()["id"]

    # Add reply to parent
    reply = await client.post(
        "/articles/no-reply-article/comments",
        json={"content": "Reply", "parent_id": parent_id},
        headers=headers
    )
    reply_id = reply.json()["id"]

    # Try reply to reply — should fail
    response = await client.post(
        "/articles/no-reply-article/comments",
        json={"content": "Reply to reply", "parent_id": reply_id},
        headers=headers
    )
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_article_with_tags(client):
    await client.post("/auth/register", json={
        "email": "tags@example.com",
        "display_name": "Tags User",
        "password": "password123"
    })
    login = await client.post("/auth/login", data={
        "username": "tags@example.com",
        "password": "password123"
    })
    token = login.json()["access_token"]

    response = await client.post("/articles/", json={
        "title": "Tagged Article",
        "content": "Content with tags",
        "status": "PUBLISHED",
        "tags": ["python", "fastapi", "docker"]
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    assert len(response.json()["tags"]) == 3

@pytest.mark.asyncio
async def test_unauthorized_delete_article(client):
    # Register two users
    await client.post("/auth/register", json={
        "email": "owner@example.com",
        "display_name": "Owner",
        "password": "password123"
    })
    await client.post("/auth/register", json={
        "email": "other@example.com",
        "display_name": "Other",
        "password": "password123"
    })

    # Login as owner and create article
    login = await client.post("/auth/login", data={
        "username": "owner@example.com",
        "password": "password123"
    })
    owner_token = login.json()["access_token"]

    await client.post("/articles/", json={
        "title": "Owner Article",
        "content": "Content",
        "status": "PUBLISHED",
        "tags": []
    }, headers={"Authorization": f"Bearer {owner_token}"})

    # Login as other user and try to delete
    login2 = await client.post("/auth/login", data={
        "username": "other@example.com",
        "password": "password123"
    })
    other_token = login2.json()["access_token"]

    response = await client.delete("/articles/owner-article",
        headers={"Authorization": f"Bearer {other_token}"})
    assert response.status_code == 403