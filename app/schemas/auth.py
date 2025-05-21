from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    mobile: Optional[str] = Field(default=None)
    email: str
    firstname: str
    lastname: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


class RegisterResponse(BaseModel):
    message: str
    # code: Optional[int] = None


class UserCreate(BaseModel):
    username: str
    password: str
    # email: Optional[str] = None
    # firstname: Optional[str] = None
    # lastname: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    is_active: bool
