"""
SPGRS – Smart Public Grievance Redressal System
Entry point: starts API + user portal (8000) and admin static server (8001).
"""
import asyncio
import sys
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from uvicorn import Config, Server

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

FRONTEND_PATH = os.path.join(_PROJECT_ROOT, "frontend")


def create_admin_static_app() -> FastAPI:
    """Lightweight app to serve admin static assets on port 8001."""
    app = FastAPI(title="SPGRS Admin Static", docs_url=None, redoc_url=None, openapi_url=None)
    if os.path.exists(FRONTEND_PATH):
        app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")

    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(os.path.join(FRONTEND_PATH, "admin", "admin_login.html"))

    return app


async def main():
    print("=" * 60)
    print("  Smart Public Grievance Redressal System (SPGRS)")
    print("=" * 60)
    print()
    print("Starting servers...")
    print("API & User Portal: http://localhost:8000")
    print("  - API Docs:      http://localhost:8000/docs")
    print("  - User Portal:   http://localhost:8000/static/user/user_login.html")
    print("Admin Portal:      http://localhost:8001/static/admin/admin_login.html")
    print()

    api_server = Server(
        Config(
            "backend.app:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info",
        )
    )

    admin_app = create_admin_static_app()
    admin_server = Server(
        Config(
            admin_app,
            host="0.0.0.0",
            port=8001,
            reload=False,
            log_level="warning",
        )
    )

    await asyncio.gather(api_server.serve(), admin_server.serve())


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
