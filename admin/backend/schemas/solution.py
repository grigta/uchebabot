"""Solution schemas for Mini App API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SolutionResponse(BaseModel):
    """Single solution response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    answer: str
    detected_subject: Optional[str]
    had_image: bool
    created_at: datetime


class SolutionListResponse(BaseModel):
    """Paginated solution list response."""

    items: List[SolutionResponse]
    total: int
    page: int
    per_page: int
