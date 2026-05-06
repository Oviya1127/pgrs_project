"""User-related Pydantic models."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """User registration model."""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=15)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model (without sensitive data)."""
    user_id: int
    full_name: str
    email: str
    phone: Optional[str]
    role: str
    created_at: datetime


class UserProfile(BaseModel):
    """User profile update model."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=15)


class AdminResponse(BaseModel):
    """Admin response model."""
    admin_id: int
    user_id: int
    full_name: str
    email: str
    created_at: datetime


class LoginResponse(BaseModel):
    """Login response with token."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
