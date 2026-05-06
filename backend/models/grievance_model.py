"""Grievance-related Pydantic models."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class GrievanceCreate(BaseModel):
    """Grievance submission model."""
    category_id: int
    location_id: int
    complaint_text: str = Field(..., min_length=10, max_length=5000)


class GrievanceUpdate(BaseModel):
    """Grievance status update model (admin)."""
    status: str = Field(..., pattern="^(SUBMITTED|IN_PROGRESS|RESOLVED)$")


class GrievanceResponse(BaseModel):
    """Grievance response model."""
    grievance_id: str
    user_id: Optional[int]
    user_name: Optional[str] = None
    category_id: int
    category_name: Optional[str] = None
    location_id: int
    location_details: Optional[str] = None
    complaint_text: str
    status: str
    created_at: datetime
    priority_level: Optional[str] = None
    compound_score: Optional[float] = None
    peer_count: Optional[int] = 0
    is_duplicate: Optional[bool] = False


class GrievanceDetail(GrievanceResponse):
    """Detailed grievance response with additional info."""
    assignment: Optional[dict] = None
    feedback: Optional[dict] = None
    duplicates: Optional[List[str]] = []


class GrievanceFilter(BaseModel):
    """Grievance filter options."""
    status: Optional[str] = None
    category_id: Optional[int] = None
    priority_level: Optional[str] = None
    location_id: Optional[int] = None
    search: Optional[str] = None  # grievance ID or user name
    page: int = 1
    per_page: int = 10


class GrievanceAssignment(BaseModel):
    """Grievance assignment model."""
    department_id: int
    admin_id: Optional[int] = None


class PeerValidation(BaseModel):
    """Peer validation response."""
    grievance_id: str
    total_validations: int
    user_validated: bool


class CategoryResponse(BaseModel):
    """Category response model."""
    category_id: int
    category_name: str


class LocationResponse(BaseModel):
    """Location response model."""
    location_id: int
    state: str
    district: str
    zone_name: Optional[str]
    ward: Optional[str]
    place_name: Optional[str]
