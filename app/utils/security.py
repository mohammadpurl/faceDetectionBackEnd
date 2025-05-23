from typing_extensions import Annotated


from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from typing import Union, Optional

from app.config import Settings

from random import randint
from app.db.session import get_db
from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict,
    settings: Annotated[Settings, Depends(get_settings)],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str, settings: Settings) -> dict:
    """
    Decode and validate JWT token
    Returns the decoded payload if valid
    Raises HTTPException if token is invalid
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token.split(" ")[1]

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Validate required fields
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.now() > datetime.fromtimestamp(exp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_refresh_token(
    data: dict,
    settings: Annotated[Settings, Depends(get_settings)],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def randomNumberGenerator() -> str:
    verification_code = randint(10000, 99999)
    return str(verification_code)
