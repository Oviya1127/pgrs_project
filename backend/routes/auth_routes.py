"""Authentication routes."""
from fastapi import APIRouter, HTTPException, status
from backend.models import UserCreate, UserLogin, BaseResponse
from backend.services import register_user, authenticate_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=BaseResponse)
async def register(user_data: UserCreate):
    """Register a new user."""
    result = await register_user(user_data)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.post("/login", response_model=BaseResponse)
async def login(credentials: UserLogin):
    """Login and get access token."""
    result = await authenticate_user(credentials.email, credentials.password)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"]
        )
    return result


@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)."""
    return {"success": True, "message": "Logged out successfully"}
