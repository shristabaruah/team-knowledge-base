# ============================================================
# auth.py — Authentication Utilities
# This file contains helper functions for:
#   1. Hashing and verifying passwords (using bcrypt)
#   2. Creating and decoding JWT access tokens
# These are pure utility functions — no FastAPI or DB code here.
# ============================================================

# datetime → used to set token expiry time
# timedelta → represents a duration (e.g. "30 minutes from now")
from datetime import datetime, timedelta

# python-jose library for working with JWTs:
# JWTError → exception raised when token is invalid/expired
# jwt     → used to encode (create) and decode (read) tokens
from jose import JWTError, jwt

# passlib is a password hashing library.
# CryptContext manages which hashing algorithm to use.
from passlib.context import CryptContext


# ---- Password Hashing Setup ----

# Create a password hashing context using bcrypt algorithm.
# bcrypt is the industry standard — it's slow by design to prevent brute-force attacks.
# deprecated="auto" → automatically handles older hash formats gracefully.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---- JWT Settings ----

# Secret key used to sign JWTs — must be kept private in production!
# Anyone with this key can forge tokens. Use an environment variable in production.
SECRET_KEY = "your-super-secret-key"  # ⚠️ Change this in production!

# The signing algorithm — HS256 is HMAC with SHA-256, the most common JWT algorithm
ALGORITHM = "HS256"

# Token expires after 30 minutes — after that, the user must log in again
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# ---- Password Functions ----

# Takes a plain-text password and returns a bcrypt hash.
# Example: hash_password("mypassword") → "$2b$12$..."
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# Checks if a plain password matches a stored hash.
# Returns True if they match, False otherwise.
# Example: verify_password("mypassword", stored_hash) → True
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---- JWT Functions ----

# Creates a signed JWT token from a data dict.
# The token contains 'data' + an expiry time ('exp').
# Returns the encoded token string (e.g. "eyJhbGc...")
def create_access_token(data: dict) -> str:
    to_encode = data.copy()  # Don't mutate the original dict

    # Set the expiry time: now + 30 minutes
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add the expiry time into the payload under the standard 'exp' key
    to_encode.update({"exp": expire})

    # Sign and encode the token using our secret key and algorithm
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Decodes and validates a JWT token.
# Returns the payload dict if valid (e.g. {"sub": "5", "exp": ...})
# Returns None if the token is expired, tampered with, or invalid.
def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Any error (expired, bad signature, etc.) → return None safely
        return None