from app.models.user import User
from app.models.user import UserPhoto
from app.db.session import get_db
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime


async def count_users() -> int:
    """
    تعداد کاربران موجود در دیتابیس را بازگرداند
    """
    try:
        async with get_db() as session:
            result = await session.execute(sa.select(sa.func.count()).select_from(User))
            count = result.scalar()
            return count
    except Exception as e:
        print(f"Error counting users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to count users: {str(e)}")


async def get_all_users() -> List[Dict[str, Any]]:
    """
    لیست تمام کاربران موجود در دیتابیس را بازگرداند
    """
    try:
        async with get_db() as session:
            result = await session.execute(sa.select(User))
            users = result.scalars().all()

            # Convert users to dict for response
            users_list = []
            for user in users:
                created_at_str = None
                if user.created_at:
                    # Convert to string safely
                    created_at_str = str(user.created_at)

                users_list.append(
                    {
                        "id": user.id,
                        "mobile": user.mobile,
                        "firstname": user.firstname,
                        "lastname": user.lastname,
                        "email": user.email,
                        "created_at": created_at_str,
                    }
                )

            return users_list
    except Exception as e:
        print(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


async def get_user_by_id(user_id: int) -> User:
    """
    اطلاعات یک کاربر را بر اساس آیدی بازگرداند
    """
    try:
        async with get_db() as session:
            result = await session.execute(sa.select(User).where(User.id == user_id))
            user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=404, detail=f"User with ID {user_id} not found"
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")


async def update_user_tokens_in_db(
    user_id: int, access_token: str, refresh_token: str, token_expires_at=None
) -> bool:
    """
    توکن‌های کاربر را در دیتابیس به‌روزرسانی کند
    """
    try:
        async with get_db() as session:
            print(f"Updating tokens for user ID: {user_id}")

            # First, get the user
            result = await session.execute(sa.select(User).where(User.id == user_id))
            user = result.scalars().first()

            if not user:
                print(f"User with ID {user_id} not found for token update")
                return False

            # Update tokens directly on the user object
            user.access_token = access_token
            user.refresh_token = refresh_token

            if token_expires_at:
                user.token_expires_at = token_expires_at

            # Make sure to commit the changes
            await session.commit()

            # Verify the tokens were updated
            result = await session.execute(sa.select(User).where(User.id == user_id))
            updated_user = result.scalars().first()

            if updated_user and updated_user.access_token == access_token:
                print(f"Tokens successfully updated for user {user_id}")
                return True
            else:
                print(f"Failed to update tokens for user {user_id}")
                return False
    except Exception as e:
        print(f"Error updating tokens in database: {e}")
        return False


async def get_user_with_tokens(user_id: int) -> Dict[str, Any]:
    """
    اطلاعات کاربر را همراه با توکن‌ها بازگرداند
    """
    try:
        async with get_db() as session:
            result = await session.execute(sa.select(User).where(User.id == user_id))
            user = result.scalars().first()

            if not user:
                raise HTTPException(
                    status_code=404, detail=f"User with ID {user_id} not found"
                )

            created_at_str = str(user.created_at) if user.created_at else None
            token_expires_at_str = (
                str(user.token_expires_at) if user.token_expires_at else None
            )

            # Only return first 10 chars of tokens for security
            access_token_preview = (
                user.access_token[:10] + "..." if user.access_token else None
            )
            refresh_token_preview = (
                user.refresh_token[:10] + "..." if user.refresh_token else None
            )

            return {
                "id": user.id,
                "mobile": user.mobile,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "email": user.email,
                "created_at": created_at_str,
                "access_token_preview": access_token_preview,
                "refresh_token_preview": refresh_token_preview,
                "has_access_token": user.access_token is not None,
                "has_refresh_token": user.refresh_token is not None,
                "token_expires_at": token_expires_at_str,
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user with tokens: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get user with tokens: {str(e)}"
        )


async def insert_user_photo_in_db(user_id: int, photo_path: str) -> bool:
    try:
        async with get_db() as session:
            new_photo = UserPhoto(user_id=user_id, image_path=photo_path)
            session.add(new_photo)
            await session.commit()
            return True
    except Exception as e:
        print(f"Error inserting user photo in database: {e}")
        return False
