from .auth_routes import router as auth_router
from .user_routes import router as user_router
from .grievance_routes import router as grievance_router
from .admin_routes import router as admin_router
from .feedback_routes import router as feedback_router
from .analytics_routes import router as analytics_router
from .upload_routes import router as upload_router

__all__ = [
    "auth_router",
    "user_router", 
    "grievance_router",
    "admin_router",
    "feedback_router",
    "analytics_router",
    "upload_router"
]
