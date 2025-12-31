"""Admin panel configuration."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdminSettings(BaseSettings):
    """Admin panel settings from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/bot.db",
        alias="DATABASE_URL",
    )

    # JWT
    jwt_secret: str = Field(alias="ADMIN_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="ADMIN_JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="ADMIN_JWT_EXPIRE_MINUTES")

    # Telegram
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        """Parse admin IDs from comma-separated string or single int."""
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "https://*.trycloudflare.com"],
    )

    # Debug
    debug: bool = Field(default=False, alias="DEBUG")


admin_settings = AdminSettings()
