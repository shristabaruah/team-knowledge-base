# Team Knowledge Base API

A production-ready RESTful API for a shared team knowledge base, built with FastAPI, PostgreSQL, Redis, and Docker.

## Tech Stack

- **Framework:** FastAPI + Uvicorn
- **Database:** PostgreSQL 16 + SQLAlchemy 2.0 + Alembic
- **Cache:** Redis 7
- **Auth:** JWT + RBAC (Admin/Member)
- **Containerization:** Docker + Docker Compose
- **Testing:** pytest + httpx

## Getting Started

### Prerequisites
- Docker Desktop installed and running
- Git

### Startup Sequence

1. Clone the repository:
```bash
git clone <your-repo-url>
cd team-knowledge-base
```

2. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

3. Run with Docker Compose:
```bash
docker compose up --build
```

4. API is available at: http://localhost:8000
5. Swagger docs: http://localhost:8000/docs
6. ReDoc: http://localhost:8000/redoc

### Optional: Seed sample data
```bash
docker compose exec api python -m app.seed
```

## API Endpoints

### Auth
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | /auth/register | Public | Register new user |
| POST | /auth/login | Public | Login, returns JWT |
| GET | /auth/me | Authenticated | Get current user |
| PATCH | /auth/me | Authenticated | Update profile |

### Articles
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | /articles/ | Public | List published articles |
| GET | /articles/{slug} | Public | Get article by slug |
| POST | /articles/ | Authenticated | Create article |
| PATCH | /articles/{slug} | Author/Admin | Update article |
| DELETE | /articles/{slug} | Author/Admin | Soft delete article |
| GET | /articles/my/drafts | Authenticated | List my drafts |

### Tags
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | /tags/ | Public | List all tags |
| POST | /tags/ | Admin | Create tag |
| GET | /tags/{slug}/articles | Public | Articles by tag |

### Comments
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | /articles/{slug}/comments | Authenticated | Add comment |
| GET | /articles/{slug}/comments | Public | List comments |
| DELETE | /articles/{slug}/comments/{id} | Author/Admin | Delete comment |

### Bookmarks
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| POST | /articles/{slug}/bookmark | Authenticated | Toggle bookmark |
| GET | /bookmarks/my | Authenticated | My bookmarks |

### Admin
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| GET | /admin/users | Admin | List all users |
| PATCH | /admin/users/{id}/role | Admin | Change user role |
| PATCH | /admin/articles/{slug}/feature | Admin | Toggle featured |
| GET | /health | Public | Health check |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql+asyncpg://... | PostgreSQL connection string |
| REDIS_URL | redis://localhost:6379 | Redis connection string |
| JWT_SECRET | your-secret-key | JWT signing secret |
| JWT_ALGORITHM | HS256 | JWT algorithm |
| ACCESS_TOKEN_EXPIRE_MINUTES | 30 | Token expiry |
| ALLOWED_ORIGINS | http://localhost:3000 | CORS allowed origins |

## Security
- JWT authentication with 30 min token expiry
- bcrypt password hashing
- CORS middleware
- Rate limiting with slowapi
- All config via environment variables

## Testing
```bash
# Run tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing -v
```

## Project Structure
```
team-knowledge-base/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── dependencies.py
│   ├── redis.py
│   └── routers/
│       ├── auth.py
│       ├── articles.py
│       ├── tags.py
│       ├── comments.py
│       ├── bookmarks.py
│       └── admin.py
├── tests/
│   └── test_articles.py
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```