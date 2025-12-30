"""Middlewares module for EduHelper Bot."""

from bot.middlewares.database import DatabaseMiddleware
from bot.middlewares.logging import LoggingMiddleware

__all__ = [
    "DatabaseMiddleware",
    "LoggingMiddleware",
]
