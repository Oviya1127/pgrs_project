"""Role-based access control middleware."""
from fastapi import HTTPException, status
from backend.utils import Roles
from backend.services import is_admin


def require_role(allowed_roles: list):
    """Decorator factory to require specific roles."""
    async def role_checker(token_data: dict):
        if token_data.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return token_data
    return role_checker


async def require_admin(token_data) -> bool:
    """Check if user is an admin."""
    if token_data.role != Roles.ADMIN:
        admin_status = await is_admin(token_data.user_id)
        if not admin_status:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
    return True


async def require_user(token_data) -> bool:
    """Check if user is authenticated (any role)."""
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return True
