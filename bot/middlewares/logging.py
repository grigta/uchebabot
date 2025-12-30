"""Logging middleware for request tracking."""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging incoming events."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        start_time = time.time()

        # Get user info if available
        user_id = None
        username = None
        event_type = type(event).__name__

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            username = event.from_user.username if event.from_user else None
            text_preview = (event.text or event.caption or "")[:50]
            logger.info(
                f"Message from {user_id} (@{username}): {text_preview}..."
                if len(text_preview) == 50
                else f"Message from {user_id} (@{username}): {text_preview}"
            )
        else:
            logger.debug(f"Event: {event_type}")

        try:
            result = await handler(event, data)
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"Handler completed in {elapsed:.2f}ms")
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(
                f"Handler error after {elapsed:.2f}ms: {type(e).__name__}: {e}",
                extra={
                    "user_id": user_id,
                    "event_type": event_type,
                },
            )
            raise
