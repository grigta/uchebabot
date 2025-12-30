"""Statistics routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from admin.backend.dependencies import get_current_admin, get_db
from admin.backend.schemas.stats import StatsResponse, SubjectCount

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from bot.database.repositories import RequestRepository, UserRepository

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_db),
    _: int = Depends(get_current_admin),
) -> StatsResponse:
    """Get dashboard statistics."""
    user_repo = UserRepository(session)
    request_repo = RequestRepository(session)

    # Get stats
    dau = await user_repo.get_active_today()
    mau = await user_repo.get_active_month()
    total_users = await user_repo.count()
    requests_today = await request_repo.count_today()
    requests_week = await request_repo.count_week()
    popular_subjects_raw = await request_repo.get_popular_subjects(limit=10)

    popular_subjects = [
        SubjectCount(subject=s["subject"], count=s["count"])
        for s in popular_subjects_raw
    ]

    # Get cost statistics
    total_cost_usd = await request_repo.get_total_cost()
    cost_today_usd = await request_repo.get_cost_today()
    cost_month_usd = await request_repo.get_cost_month()
    avg_cost_per_request = await request_repo.get_avg_cost_per_request()
    avg_tokens_per_request = await request_repo.get_avg_tokens_per_request()

    return StatsResponse(
        dau=dau,
        mau=mau,
        total_users=total_users,
        requests_today=requests_today,
        requests_week=requests_week,
        popular_subjects=popular_subjects,
        # Cost statistics
        total_cost_usd=round(total_cost_usd, 4),
        cost_today_usd=round(cost_today_usd, 4),
        cost_month_usd=round(cost_month_usd, 4),
        avg_cost_per_request=round(avg_cost_per_request, 6),
        avg_tokens_per_request=round(avg_tokens_per_request, 1),
    )
