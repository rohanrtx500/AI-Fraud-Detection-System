import os
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.api.dependencies import get_db_session
from src.database.models import User

# In a production environment, these settings would be loaded from pydantic-settings / .env
SECRET_KEY = "SUPER_SECRET_COMPLIANCE_KEY_FOR_JWT_SIGNING_AND_SECURITY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate session credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            role_id: str = payload.get("sub")
            if role_id is None:
                raise credentials_exception
        except jwt.PyJWTError:
            raise credentials_exception from None

        result = await db.execute(select(User).where(User.role_id == role_id))
        user = result.scalars().first()
        if user is None:
            raise credentials_exception
        return user

    # Backwards compatibility check: fall back to X-API-KEY if present and valid
    api_key = request.headers.get("X-API-KEY")
    expected_key = os.getenv("API_KEY", "fraud_dev_sec_key")
    if api_key and api_key == expected_key:
        return User(username="system", role="Compliance Officer")

    raise credentials_exception


def get_required_role(allowed_roles: list[str]):
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Action denied: insufficient permissions for this user role",
            )
        return current_user

    return dependency
