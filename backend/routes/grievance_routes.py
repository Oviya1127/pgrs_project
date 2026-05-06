"""Grievance routes."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from backend.models import GrievanceCreate, GrievanceFilter, BaseResponse
from backend.middleware import get_current_user
from backend.services import (
    create_grievance, get_user_grievances, get_grievance_by_id,
    add_peer_validation, get_categories, get_locations, find_similar_grievances
)

router = APIRouter(prefix="/grievances", tags=["Grievances"])


@router.post("/", response_model=BaseResponse)
async def submit_grievance(grievance: GrievanceCreate, current_user = Depends(get_current_user)):
    """Submit a new grievance."""
    result = await create_grievance(current_user.user_id, grievance)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.get("/")
async def get_my_grievances(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    current_user = Depends(get_current_user)
):
    """Get current user's grievances."""
    result = await get_user_grievances(current_user.user_id, page, per_page)
    return result


@router.get("/categories")
async def list_categories():
    """Get all grievance categories."""
    categories = await get_categories()
    return {"success": True, "data": categories}


@router.get("/locations")
async def list_locations():
    """Get all locations."""
    locations = await get_locations()
    return {"success": True, "data": locations}


@router.get("/similar")
async def get_similar_grievances(
    category_id: int,
    location_id: int,
    complaint_text: str,
    current_user = Depends(get_current_user)
):
    """Find similar grievances for duplicate detection."""
    similar = await find_similar_grievances(category_id, location_id, complaint_text)
    return {"success": True, "data": similar}


@router.get("/{grievance_id}")
async def get_grievance_detail(grievance_id: str, current_user = Depends(get_current_user)):
    """Get grievance details."""
    result = await get_grievance_by_id(grievance_id, current_user.user_id)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    return result


@router.post("/{grievance_id}/validate")
async def validate_grievance(grievance_id: str, current_user = Depends(get_current_user)):
    """Add peer validation to a grievance."""
    result = await add_peer_validation(grievance_id, current_user.user_id)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result
