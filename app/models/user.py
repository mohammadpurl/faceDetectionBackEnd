from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    mobile: Mapped[str | None] = mapped_column(
        String, unique=True, index=True, nullable=True
    )
    firstname: Mapped[str | None] = mapped_column(String, nullable=True)
    lastname: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    national_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    verification_code: Mapped[str | None] = mapped_column(String, nullable=True)
    verification_code_expires: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    access_token: Mapped[str | None] = mapped_column(String, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    photos: Mapped[list["UserPhoto"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserPhoto(Base):
    __tablename__ = "user_photos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="photos")
