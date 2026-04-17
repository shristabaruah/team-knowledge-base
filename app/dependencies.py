# ============================================================
# dependencies.py — Reusable FastAPI Dependencies
# FastAPI "dependencies" are functions injected into route handlers
# via Depends(). This file provides two key dependencies:
#   1. get_current_user → extracts & validates the logged-in user from the JWT
#   2. require_role     → checks the user's role (ADMIN / MEMBER)
# ============================================================

# Depends      → tells FastAPI to inject the result of a function into a route
# HTTPException → raises an HTTP error response (e.g. 401, 403)
# status       → contains HTTP status code constants (e.g. status.HTTP_401_UNAUTHORIZED)
from fastapi import Depends, HTTPException, status

# OAuth2PasswordBearer → extracts the Bearer token from the Authorization header.
# tokenUrl tells Swagger UI where to send login requests (used for the "Authorize" button).
from fastapi.security import OAuth2PasswordBearer

# AsyncSession is the type for our async database session (used as a type hint)
from sqlalchemy.ext.asyncio import AsyncSession

# Import the get_db dependency to get a database session
from app.database import get_db

# Import User model (to fetch from DB) and UserRole enum (for role checks)
from app.models import User, UserRole

# Import our decode_token utility to validate and read the JWT
from app.auth import decode_token


# This object extracts the Bearer token from the "Authorization: Bearer <token>" header.
# FastAPI automatically handles reading this from the request header.
# tokenUrl="/auth/login" is just metadata for Swagger UI's Authorize button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---- get_current_user ----
# This is a FastAPI dependency injected into protected routes.
# It reads the JWT token from the request header, validates it,
# and returns the currently logged-in User object from the database.
# If the token is missing, expired, or invalid → raises 401 Unauthorized.
async def get_current_user(
    token: str = Depends(oauth2_scheme),  # FastAPI extracts the token from Authorization header
    db: AsyncSession = Depends(get_db)    # FastAPI injects a DB session
) -> User:

    # Pre-define the error we'll raise if anything goes wrong
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},  # Standard OAuth2 header
    )

    # Decode the JWT token → returns payload dict or None if invalid
    payload = decode_token(token)
    if not payload:
        raise credentials_exception  # Token is invalid or expired

    # 'sub' (subject) stores the user's ID — set during login in create_access_token()
    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception  # Token doesn't contain a user ID

    # Fetch the user from the database by ID
    # db.get() is a shortcut for fetching by primary key
    user = await db.get(User, int(user_id))
    if not user:
        raise credentials_exception  # User was deleted after the token was issued

    # Return the authenticated User object — injected into the route handler
    return user


# ---- require_role ----
# A role-based access control (RBAC) factory function.
# It returns a FastAPI dependency that checks if the current user has the required role.
# Usage: Depends(require_role(UserRole.ADMIN))
#
# How it works:
#   require_role(UserRole.ADMIN) → returns role_checker function
#   role_checker is called by FastAPI via Depends() and:
#     - First calls get_current_user to get the logged-in user
#     - Then checks if their role matches the required role
#     - Raises 403 Forbidden if not
def require_role(required_role: UserRole):
    # Inner async function — this is the actual FastAPI dependency
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user  # Return the user if role check passes
    return role_checker


# ---- Convenience shortcuts ----
# Pre-built dependencies for common role checks.
# Use Depends(require_admin) in any route that only admins can access.
# Use Depends(require_member) in any route that only members can access.
require_admin = require_role(UserRole.ADMIN)
require_member = require_role(UserRole.MEMBER)