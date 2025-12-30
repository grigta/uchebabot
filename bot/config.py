"""Bot configuration using Pydantic Settings."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    # OpenRouter
    openrouter_api_key: str = Field(alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="google/gemini-2.0-flash-001",
        alias="OPENROUTER_MODEL",
    )
    openrouter_max_tokens: int = Field(default=2000, alias="OPENROUTER_MAX_TOKENS")
    openrouter_temperature: float = Field(default=0.7, alias="OPENROUTER_TEMPERATURE")
    openrouter_timeout: int = Field(default=60, alias="OPENROUTER_TIMEOUT")

    # OpenRouter pricing (per token) - Gemini 3.0 Flash
    # $0.50 / 1M input tokens, $3.00 / 1M output tokens
    openrouter_input_price: float = Field(default=0.0000005, alias="OPENROUTER_INPUT_PRICE")
    openrouter_output_price: float = Field(default=0.000003, alias="OPENROUTER_OUTPUT_PRICE")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/bot.db",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Rate Limiting
    daily_request_limit: int = Field(default=20, alias="DAILY_REQUEST_LIMIT")

    # YooKassa
    yookassa_shop_id: str = Field(default="", alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(default="", alias="YOOKASSA_SECRET_KEY")

    # Prices in Telegram Stars (1 star ≈ 2 RUB)
    price_50_requests_stars: int = Field(default=75, alias="PRICE_50_REQUESTS_STARS")
    price_100_requests_stars: int = Field(default=115, alias="PRICE_100_REQUESTS_STARS")
    price_subscription_stars: int = Field(default=200, alias="PRICE_SUBSCRIPTION_STARS")

    # Prices in RUB (kopecks for YooKassa)
    price_50_requests_rub: int = Field(default=14900, alias="PRICE_50_REQUESTS_RUB")
    price_100_requests_rub: int = Field(default=22900, alias="PRICE_100_REQUESTS_RUB")
    price_subscription_rub: int = Field(default=39900, alias="PRICE_SUBSCRIPTION_RUB")

    # Admin Panel
    admin_jwt_secret: str = Field(alias="ADMIN_JWT_SECRET")
    admin_jwt_algorithm: str = Field(default="HS256", alias="ADMIN_JWT_ALGORITHM")
    admin_jwt_expire_minutes: int = Field(
        default=1440, alias="ADMIN_JWT_EXPIRE_MINUTES"
    )

    # Mini App
    webapp_url: str = Field(default="", alias="WEBAPP_URL")

    # App Settings
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return "sqlite" in self.database_url.lower()


settings = Settings()
