"""Base Pydantic models and response schemas."""
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


class BaseResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool
    message: str
    data: Optional[Any] = None


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: int
    email: str
    role: str
    exp: Optional[datetime] = None


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
