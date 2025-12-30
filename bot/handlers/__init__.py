"""Handlers module for EduHelper Bot."""

from aiogram import Router

from bot.handlers.help import router as help_router
from bot.handlers.payment import router as payment_router
from bot.handlers.profile import router as profile_router
from bot.handlers.question import router as question_router
from bot.handlers.start import router as start_router


def setup_routers() -> Router:
    """Setup and return main router with all handlers."""
    main_router = Router()

    # Include all routers
    main_router.include_router(start_router)
    main_router.include_router(profile_router)
    main_router.include_router(payment_router)
    main_router.include_router(help_router)
    main_router.include_router(question_router)

    return main_router


__all__ = ["setup_routers"]
