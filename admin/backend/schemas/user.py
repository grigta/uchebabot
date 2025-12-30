"""User schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """User response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    daily_requests: int
    total_requests: int
    total_tokens: int
    is_banned: bool
    custom_daily_limit: Optional[int]
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """User update schema."""

    is_banned: Optional[bool] = None
    custom_daily_limit: Optional[int] = None


class UserListResponse(BaseModel):
    """Paginated user list response."""

    items: List[UserResponse]
    total: int
    page: int
    per_page: int
