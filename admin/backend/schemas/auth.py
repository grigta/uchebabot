"""Authentication schemas."""

from typing import Optional

from pydantic import BaseModel


class TelegramAuthData(BaseModel):
    """Data from Telegram Login Widget."""

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
