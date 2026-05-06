"""Main FastAPI application: API + static user portal on port 8000."""
import sys
import os

# Ensure project root is on path when app is loaded by uvicorn (e.g. run.py)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from config import get_settings
from backend.utils import get_pool, close_pool
from backend.models import HealthCheck
from backend.routes import (
    auth_router,
    user_router,
    grievance_router,
    admin_router,
    feedback_router,
    analytics_router,
    upload_router,
)
from backend.services.upload_service import ensure_attachments_table

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await get_pool()
    print("Database connection pool initialized")
    await ensure_attachments_table()
    print("Grievance attachments table ensured")
    yield
    await close_pool()
    print("Database connection pool closed")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Smart Public Grievance Redressal System API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(_PROJECT_ROOT, "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(grievance_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(upload_router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root():
    """Serve the user login page."""
    return FileResponse(os.path.join(frontend_path, "user", "user_login.html"))


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    return HealthCheck(status="healthy", version=settings.APP_VERSION)


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "auth": "/api/auth",
            "user": "/api/user",
            "grievances": "/api/grievances",
            "admin": "/api/admin",
            "feedback": "/api/feedback",
            "analytics": "/api/analytics",
        },
    }
