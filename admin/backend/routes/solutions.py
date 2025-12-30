"""Solutions API routes for Mini App."""

import hashlib
import hmac
import json
import logging
from typing import Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from admin.backend.config import admin_settings
from admin.backend.dependencies import get_db
from admin.backend.schemas.solution import SolutionListResponse, SolutionResponse
from bot.database.repositories import RequestRepository

router = APIRouter(prefix="/api/solutions", tags=["solutions"])
logger = logging.getLogger(__name__)


def validate_init_data(init_data: str, bot_token: str) -> Optional[int]:
    """
    Validate Telegram Mini App initData.

    Returns telegram_id if valid, None otherwise.

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # Parse initData as query string
        parsed = parse_qs(init_data, keep_blank_values=True)

        # Extract hash
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return None

        # Build data-check-string (sorted alphabetically, excluding hash)
        data_check_parts = []
        for key, values in sorted(parsed.items()):
            if key != "hash":
                data_check_parts.append(f"{key}={values[0]}")

        data_check_string = "\n".join(data_check_parts)

        # Create secret key: HMAC-SHA256(bot_token, "WebAppData")
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Compare hashes
        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        # Extract user data
        user_data_str = parsed.get("user", [None])[0]
        if not user_data_str:
            return None

        user_data = json.loads(user_data_str)
        return user_data.get("id")

    except Exception as e:
        logger.warning(f"initData validation failed: {e}")
        return None


async def get_telegram_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data")
) -> int:
    """Dependency to validate Telegram initData and return user ID."""
    telegram_id = validate_init_data(
        x_telegram_init_data,
        admin_settings.telegram_bot_token
    )

    if telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication"
        )

    return telegram_id


@router.get("/my", response_model=SolutionListResponse)
async def get_my_solutions(
    telegram_id: int = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    """Get all solutions for the authenticated user."""
    repo = RequestRepository(db)

    offset = (page - 1) * per_page

    # Get solutions and total count
    solutions = await repo.get_user_requests_by_telegram_id(
        telegram_id=telegram_id,
        offset=offset,
        limit=per_page,
    )
    total = await repo.count_user_requests_by_telegram_id(telegram_id)

    return SolutionListResponse(
        items=[SolutionResponse.model_validate(s) for s in solutions],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{solution_id}", response_model=SolutionResponse)
async def get_solution(
    solution_id: int,
    telegram_id: int = Depends(get_telegram_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific solution by ID (must belong to the user)."""
    repo = RequestRepository(db)

    solution = await repo.get_by_id_and_telegram_id(
        request_id=solution_id,
        telegram_id=telegram_id,
    )

    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )

    return SolutionResponse.model_validate(solution)
