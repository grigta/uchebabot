"""Admin panel FastAPI application."""

import sys
from pathlib import Path

# Add parent directory for bot imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from admin.backend.config import admin_settings
from admin.backend.routes import auth_router, stats_router, users_router, webhook_router
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "admin.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=admin_settings.debug,
    )
