from typing import Optional
from app.config import Settings, get_settings
from app.utils.security import (
    hash_password,
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.schemas.auth import (
    RegisterRequest,
    TokenResponse,
    RegisterResponse,
    UserCreate,
)
from app.db.session import get_db
from app.models.user import User
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
from sqlalchemy.future import select
from jwt import ExpiredSignatureError
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status

# from jose import jwt, JWTError

from typing_extensions import Annotated
from datetime import datetime, timedelta
import logging
from app.services.user_service import get_user_by_id
from app.utils.security import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)

# OAuth2PasswordBearer for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)

# Optional OAuth2 scheme for endpoints that can work with or without authentication
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


async def handle_verify_code(mobile: str, code: int) -> str:
    """اعتبارسنجی کد تأیید و صدور توکن"""
    user = await get_user_by_mobile(mobile)

    if not user or str(user.verification_code) != str(code):
        raise HTTPException(status_code=400, detail="Invalid verification code")

    if user.verification_code_expires < datetime.now():
        raise HTTPException(status_code=400, detail="Verification code expired")

    # صدور توکن
    access_token = create_access_token(
        data={"mobile": mobile},
        settings=get_settings(),
    )
    print(access_token)
    return access_token


async def refresh_access_token(
    refresh_token: str,
    db: AsyncSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse | None:
    """
    بررسی اعتبار Refresh Token و تولید Access Token جدید
    """
    try:
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        mobile = payload.get("mobile")
        if not mobile:
            return None

        user = await get_user_by_mobile(mobile)
        if not user or user.refresh_token != refresh_token:
            return None

        # تولید Access Token جدید
        new_access_token = create_access_token(
            data={"mobile": mobile},
            settings=get_settings(),
        )
        refresh_token = create_refresh_token(
            data={"mobile": mobile},
            settings=get_settings(),
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_at=user.token_expires_at,
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


async def get_user_by_mobile(mobile: str):
    async with get_db() as session:
        result = await session.execute(sa.select(User).where(User.mobile == mobile))
        user = result.scalars().first()
        return user


# Token validation and user extraction
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    """
    احراز هویت کاربر از طریق توکن JWT و بازگرداندن شناسه کاربر.
    این تابع برای API‌هایی استفاده می‌شود که نیاز به احراز هویت اجباری دارند.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="اعتبار نشست شما منقضی شده است. لطفا دوباره وارد شوید.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        logger.warning("No token provided in request")
        raise credentials_exception

    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token.split(" ")[1]

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        sub = payload.get("sub")

        if not sub:
            logger.warning("Token is missing user_id")
            raise credentials_exception

        user_id = int(sub)

        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.now() > datetime.fromtimestamp(exp):
            logger.warning(f"Token expired for user_id {user_id}")
            raise credentials_exception

    except JWTError as e:
        logger.warning(f"JWT Error: {str(e)}")
        raise credentials_exception
    except ValueError as e:
        logger.warning(f"Invalid token format: {str(e)}")
        raise credentials_exception

    # Check if user exists in database
    user = await get_user_by_id(user_id)
    if user is None:
        logger.warning(f"User ID {user_id} from token not found in database")
        raise credentials_exception

    return user


async def create_user(user_data: UserCreate, db: AsyncSession) -> User:
    """Create a new user with hashed password"""
    hashed_password = hash_password(user_data.password)
    username = user_data.username
    # First check if user exists by mobile
    user_result = await get_user_by_username(username)
    if user_result:
        print(
            f"User already exists with username {username}. Updating verification code."
        )
        return user_result

    # User doesn't exist, create new user
    expires_at = datetime.now() + timedelta(minutes=5)
    current_time = datetime.now()

    try:
        async with get_db() as session:
            print(f"Creating new user with username {username}")
            new_user = User(
                username=username,
                hashed_password=hashed_password,
                verification_code_expires=expires_at,
                updated_at=current_time,
            )

            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            print(f"Successfully created new user with ID {new_user.id}")
            return new_user
    except IntegrityError as e:
        print(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")
    except Exception as e:
        print(f"Unexpected error creating user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user and return user object"""
    user = await get_user_by_username(username)
    print(f"authenticate_user: {user}")
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username"""
    async with get_db() as session:
        result = await session.execute(sa.select(User).where(User.username == username))
        user = result.scalars().first()
        return user


async def create_tokens(user: User) -> dict:
    try:
        print(f"Creating tokens for user ID: {user.id}, mobile: {user.mobile}")
        settings = get_settings()

        # Calculate token expiration
        access_token_expires = datetime.now() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        refresh_token_expires = datetime.now() + timedelta(days=7)

        # Define default scopes for user
        scopes = ["user"]  # همه کاربران به اطلاعات پایه دسترسی دارند

        # اضافه کردن دسترسی‌های دیگر بر اساس نوع کاربر
        if getattr(user, "is_admin", False):
            scopes.extend(["products", "categories", "warehouses"])
        elif getattr(user, "is_supplier", False):
            scopes.extend(["products", "warehouses"])

        # Create tokens with scopes
        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username, "scopes": scopes},
            settings=settings,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "username": user.mobile, "username": scopes},
            settings=settings,
            expires_delta=None,
        )

        # Store tokens in the database
        print(f"Storing tokens in database for user ID: {user.id}")
        token_updated = await update_user_tokens_in_db(
            username=user.username,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=access_token_expires,
        )

        if not token_updated:
            print(f"Warning: Failed to update tokens for user ID: {user.id}")
        else:
            print(f"Tokens created and stored successfully for user ID: {user.id}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_at": access_token_expires,
        }
    except Exception as e:
        print(f"Error creating tokens: {e}")
        raise


async def update_user_tokens_in_db(
    username: str, access_token: str, refresh_token: str, token_expires_at=None
) -> bool:
    """
    توکن‌های کاربر را در دیتابیس به‌روزرسانی کند
    """
    try:
        async with get_db() as session:
            print(f"Updating tokens for username: {username}")

            # First, get the user
            result = await session.execute(
                sa.select(User).where(User.username == username)
            )
            user = result.scalars().first()

            if not user:
                print(f"User with username {username} not found for token update")
                return False

            # Update tokens directly on the user object
            user.access_token = access_token
            user.refresh_token = refresh_token

            if token_expires_at:
                user.token_expires_at = token_expires_at

            # Make sure to commit the changes
            await session.commit()

            # Verify the tokens were updated
            result = await session.execute(
                sa.select(User).where(User.username == username)
            )
            updated_user = result.scalars().first()

            if updated_user and updated_user.access_token == access_token:
                print(f"Tokens successfully updated for user {username}")
                return True
            else:
                print(f"Failed to update tokens for user {username}")
                return False
    except Exception as e:
        print(f"Error updating tokens in database: {e}")
        return False
