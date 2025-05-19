from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.services.auth import (
    refresh_access_token,
    create_access_token,
    get_current_user,
    get_settings,
    get_user_by_mobile,
    create_user,
    authenticate_user,
    create_tokens,
)
from sqlalchemy.future import select
from datetime import timedelta, datetime
from app.schemas.auth import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from fastapi.security import OAuth2PasswordRequestForm
from app.config import Settings
from app.services.auth import update_user_tokens_in_db, get_user_by_username


router = APIRouter()


@router.post("/token")
async def login_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_by_username(form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    settings = get_settings()
    scopes = ["user"]  # همه کاربران به اطلاعات پایه دسترسی دارند

    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "scopes": scopes},
        settings=settings,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    refresh_token: str, db: AsyncSession = Depends(get_db)
):
    """
    مسیر دریافت Access Token جدید با Refresh Token
    """
    new_access_token = await refresh_access_token(
        refresh_token,
        db,
        settings=get_settings(),
    )
    if not new_access_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return new_access_token


@router.get("/protected-route")
async def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": "This is a protected route", "user": current_user}


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Register a new user"""
    user = await create_user(user_data, db)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        firstname=user.firstname,
        lastname=user.lastname,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Login user and return tokens"""
    user = await authenticate_user(user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = await create_tokens(user)
    await update_user_tokens_in_db(
        user, tokens["access_token"], tokens["refresh_token"], tokens.get("expires_at")
    )

    return TokenResponse(**tokens)


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        firstname=current_user.firstname,
        lastname=current_user.lastname,
        is_active=current_user.is_active,
    )
