"""Statistics schemas."""

from pydantic import BaseModel


class SubjectCount(BaseModel):
    """Subject with count."""

    subject: str
    count: int


class StatsResponse(BaseModel):
    """Statistics response."""

    dau: int
    mau: int
    total_users: int
    requests_today: int
    requests_week: int
    popular_subjects: list[SubjectCount]

    # Cost statistics
    total_cost_usd: float
    cost_today_usd: float
    cost_month_usd: float
    avg_cost_per_request: float
    avg_tokens_per_request: float
