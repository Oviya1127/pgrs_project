"""User routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from backend.models import UserProfile, BaseResponse
from backend.middleware import get_current_user
from backend.services import get_user_by_id, update_user_profile, get_user_notifications, mark_as_read, mark_all_as_read, get_unread_count

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/profile", response_model=BaseResponse)
async def get_profile(current_user = Depends(get_current_user)):
    """Get current user profile."""
    user = await get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"success": True, "message": "Profile retrieved", "data": user}


@router.put("/profile", response_model=BaseResponse)
async def update_profile(profile: UserProfile, current_user = Depends(get_current_user)):
    """Update user profile."""
    result = await update_user_profile(
        current_user.user_id,
        full_name=profile.full_name,
        phone=profile.phone
    )
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.get("/notifications")
async def get_notifications(unread_only: bool = False, current_user = Depends(get_current_user)):
    """Get user notifications."""
    notifications = await get_user_notifications(current_user.user_id, unread_only)
    unread_count = await get_unread_count(current_user.user_id)
    return {
        "success": True,
        "data": {
            "notifications": notifications,
            "unread_count": unread_count
        }
    }


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: int, current_user = Depends(get_current_user)):
    """Mark a notification as read."""
    result = await mark_as_read(notification_id, current_user.user_id)
    return result


@router.put("/notifications/read-all")
async def mark_all_notifications_read(current_user = Depends(get_current_user)):
    """Mark all notifications as read."""
    result = await mark_all_as_read(current_user.user_id)
    return result
