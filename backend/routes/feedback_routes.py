"""Feedback routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from backend.models import FeedbackCreate, BaseResponse
from backend.middleware import get_current_user
from backend.utils import db, Messages

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("/", response_model=BaseResponse)
async def submit_feedback(feedback: FeedbackCreate, current_user = Depends(get_current_user)):
    """Submit feedback for a resolved grievance."""
    grievance = await db.fetch_one(
        "SELECT grievance_id, status, user_id FROM grievances WHERE grievance_id = $1",
        feedback.grievance_id
    )
    
    if not grievance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=Messages.GRIEVANCE_NOT_FOUND
        )
    
    if grievance['status'] != 'RESOLVED':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit feedback for resolved grievances"
        )
    
    existing = await db.fetch_one(
        "SELECT feedback_id FROM feedback WHERE grievance_id = $1 AND user_id = $2",
        feedback.grievance_id, current_user.user_id
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback already submitted for this grievance"
        )
    
    result = await db.fetch_one(
        """
        INSERT INTO feedback (grievance_id, user_id, rating, comments)
        VALUES ($1, $2, $3, $4)
        RETURNING feedback_id, grievance_id, rating, comments, submitted_at
        """,
        feedback.grievance_id,
        current_user.user_id,
        feedback.rating,
        feedback.comments
    )
    
    return {
        "success": True,
        "message": Messages.FEEDBACK_SUBMITTED,
        "data": dict(result)
    }


@router.get("/{grievance_id}")
async def get_feedback(grievance_id: str, current_user = Depends(get_current_user)):
    """Get feedback for a grievance."""
    feedback = await db.fetch_one(
        """
        SELECT f.feedback_id, f.grievance_id, f.user_id, u.full_name as user_name,
               f.rating, f.comments, f.submitted_at
        FROM feedback f
        JOIN users u ON f.user_id = u.user_id
        WHERE f.grievance_id = $1
        """,
        grievance_id
    )
    
    if not feedback:
        return {"success": True, "data": None}
    
    return {"success": True, "data": dict(feedback)}
