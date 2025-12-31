"""Admin panel FastAPI application."""

import sys
from pathlib import Path

# Add parent directory for bot imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from admin.backend.config import admin_settings
from admin.backend.routes import (
    auth_router,
    solutions_router,
    stats_router,
    users_router,
    webhook_router,
)
from bot.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="EduHelper Admin API",
    description="Admin panel API for EduHelper Bot",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=admin_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(stats_router)
app.include_router(webhook_router)
app.include_router(solutions_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Serve Mini App static files
webapp_dist = Path(__file__).parent.parent.parent / "webapp" / "dist"
if webapp_dist.exists():
    # Mount static assets
    app.mount(
        "/webapp/assets",
        StaticFiles(directory=webapp_dist / "assets"),
        name="webapp-assets"
    )

    # SPA fallback for Mini App routes
    @app.get("/webapp/{path:path}")
    async def serve_webapp(path: str):
        """Serve Mini App with SPA fallback."""
        file_path = webapp_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Fallback to index.html for SPA routing
        return FileResponse(webapp_dist / "index.html")

    @app.get("/webapp")
    async def serve_webapp_root():
        """Serve Mini App root."""
        return FileResponse(webapp_dist / "index.html")


# Serve Admin Panel static files
admin_dist = Path(__file__).parent.parent / "frontend" / "dist"
if admin_dist.exists():
    # Mount static assets
    app.mount(
        "/admin/assets",
        StaticFiles(directory=admin_dist / "assets"),
        name="admin-assets"
    )

    # SPA fallback for Admin Panel routes
    @app.get("/admin/{path:path}")
    async def serve_admin(path: str):
        """Serve Admin Panel with SPA fallback."""
        file_path = admin_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Fallback to index.html for SPA routing
        return FileResponse(admin_dist / "index.html")

    @app.get("/admin")
    async def serve_admin_root():
        """Serve Admin Panel root."""
        return FileResponse(admin_dist / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "admin.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=admin_settings.debug,
    )
