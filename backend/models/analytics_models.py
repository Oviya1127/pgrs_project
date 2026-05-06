"""Analytics-related models (sentiment, priority, departments)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SentimentResponse(BaseModel):
    """Sentiment analysis response."""
    sentiment_id: int
    grievance_id: str
    compound_score: float
    analyzed_at: datetime


class SentimentCreate(BaseModel):
    """Sentiment analysis creation."""
    grievance_id: str
    compound_score: float


class PriorityResponse(BaseModel):
    """Priority response."""
    priority_id: int
    grievance_id: str
    priority_level: str
    calculated_at: datetime


class PriorityCreate(BaseModel):
    """Priority creation."""
    grievance_id: str
    priority_level: str


class DepartmentResponse(BaseModel):
    """Department response."""
    department_id: int
    department_name: str
    trust_score: float


class DepartmentPerformance(BaseModel):
    """Department performance metrics."""
    department_id: int
    department_name: str
    trust_score: float
    total_assigned: int
    total_resolved: int
    resolution_rate: float
    avg_resolution_time: Optional[float] = None


class AssignmentResponse(BaseModel):
    """Assignment response."""
    assignment_id: int
    grievance_id: str
    department_id: int
    department_name: str
    admin_id: Optional[int]
    admin_name: Optional[str]
    assigned_at: datetime
