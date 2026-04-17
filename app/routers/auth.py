from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User
from app.auth import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user
from app.schemas import RegisterRequest, TokenResponse, UserResponse, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])

# REGISTER
@router.post("/register", status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        display_name=data.display_name,
        password_hash=hash_password(data.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"message": "User registered successfully"}

# LOGIN
@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}

# GET CURRENT USER
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# UPDATE PROFILE
@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, key, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user