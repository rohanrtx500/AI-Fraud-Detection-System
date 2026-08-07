import random
import re
from datetime import timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.dependencies import get_db_session
from src.api.schemas.auth import Token, UserCreate, UserResponse
from src.api.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from src.database.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db_session)):
    # 1. Validate password strength
    password = user_in.password
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter.",
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter.",
        )
    if not re.search(r"[0-9]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number.",
        )
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character (!@#$%^&* etc.).",
        )

    # 2. Validate role input
    allowed_roles = ["Compliance Officer", "Analyst", "Auditor"]
    if user_in.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(allowed_roles)}",
        )

    # 3. Generate unique role_id
    role_prefix_map = {
        "Compliance Officer": "CO",
        "Analyst": "AN",
        "Auditor": "AU",
    }
    role_prefix = role_prefix_map[user_in.role]

    role_id = None
    # Generate unique 4-digit ID
    for _ in range(100):
        rand_num = random.randint(1000, 9999)
        candidate_id = f"{role_prefix}-{rand_num}"
        result = await db.execute(select(User).where(User.role_id == candidate_id))
        if result.scalars().first() is None:
            role_id = candidate_id
            break

    if not role_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate a unique role ID. Please try again.",
        )

    # 4. Save clean full name as username
    raw_name = user_in.username.strip()
    clean_username = " ".join(raw_name.split())

    hashed_pwd = get_password_hash(password)
    new_user = User(
        username=clean_username,
        hashed_password=hashed_pwd,
        role=user_in.role,
        role_id=role_id,
    )
    db.add(new_user)
    await db.flush()
    return new_user


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(
        select(User).where(User.role_id == form_data.username)
    )
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Role ID or password combination",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.role_id, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
        "role_id": user.role_id,
    }


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
