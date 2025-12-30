"""User management routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from admin.backend.dependencies import get_current_admin, get_db
from admin.backend.schemas.user import UserListResponse, UserResponse, UserUpdate

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from bot.database.repositories import UserRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_admin),
) -> UserListResponse:
    """Get paginated list of users."""
    repo = UserRepository(session)

    offset = (page - 1) * per_page
    users = await repo.get_all(offset=offset, limit=per_page, search=search)
    total = await repo.count(search=search)

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_admin),
) -> UserResponse:
    """Get user by ID."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserUpdate,
    session: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_admin),
) -> UserResponse:
    """Update user (ban/unban, set custom limit)."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if update_data.is_banned is not None:
        await repo.set_banned(user_id, update_data.is_banned)

    if update_data.custom_daily_limit is not None:
        await repo.set_custom_limit(user_id, update_data.custom_daily_limit)

    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/{user_id}/ban", response_model=UserResponse)
async def ban_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_admin),
) -> UserResponse:
    """Ban user."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await repo.set_banned(user_id, True)
    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/{user_id}/unban", response_model=UserResponse)
async def unban_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_admin),
) -> UserResponse:
    """Unban user."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await repo.set_banned(user_id, False)
    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)
