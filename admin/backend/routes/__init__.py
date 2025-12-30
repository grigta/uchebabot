"""Admin API routes."""

from admin.backend.routes.auth import router as auth_router
from admin.backend.routes.stats import router as stats_router
from admin.backend.routes.users import router as users_router
from admin.backend.routes.webhook import router as webhook_router

__all__ = [
    "auth_router",
    "users_router",
    "stats_router",
    "webhook_router",
]
