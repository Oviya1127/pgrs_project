from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FeedbackCreate(BaseModel):
    grievance_id: str
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=1000)


class FeedbackResponse(BaseModel):
    feedback_id: int
    grievance_id: str
    user_id: int
    user_name: Optional[str] = None
    rating: int
    comments: Optional[str]
    submitted_at: datetime


class NotificationResponse(BaseModel):
    notification_id: int
    user_id: int
    message: str
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: int
    message: str
