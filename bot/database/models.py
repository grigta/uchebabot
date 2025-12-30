"""SQLAlchemy models for EduHelper Bot."""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, Text, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models with async attributes support."""

    pass


class PaymentProvider(str, enum.Enum):
    """Payment provider types."""

    TELEGRAM_STARS = "stars"
    YOOKASSA = "yookassa"


class PaymentStatus(str, enum.Enum):
    """Payment status types."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class PackageType(str, enum.Enum):
    """Package types for purchase."""

    REQUESTS_50 = "requests_50"
    REQUESTS_100 = "requests_100"
    REQUESTS_500 = "requests_500"
    SUBSCRIPTION = "subscription"


class User(Base):
    """User model representing Telegram users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Usage stats
    daily_requests: Mapped[int] = mapped_column(default=0)
    total_requests: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    total_cost_usd: Mapped[float] = mapped_column(default=0.0)  # Total cost in USD
    last_request_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    bonus_requests: Mapped[int] = mapped_column(default=0)  # Purchased requests (don't reset)

    # Status
    is_banned: Mapped[bool] = mapped_column(default=False)
    custom_daily_limit: Mapped[Optional[int]] = mapped_column(nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    requests: Mapped[List["Request"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["Payment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Request(Base):
    """Request model for storing user questions and AI responses."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Content
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    detected_subject: Mapped[Optional[str]] = mapped_column(nullable=True)

    # AI stats (per-stage tokens from final request, kept for backward compatibility)
    model_used: Mapped[str] = mapped_column()
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    response_time_ms: Mapped[int] = mapped_column(default=0)

    # Aggregated AI stats (sum of all stages: interview + plan + solution)
    total_prompt_tokens: Mapped[int] = mapped_column(default=0)
    total_completion_tokens: Mapped[int] = mapped_column(default=0)
    total_all_tokens: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)  # Cost in USD for this request

    # Flags
    had_image: Mapped[bool] = mapped_column(default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="requests")

    def __repr__(self) -> str:
        return f"<Request(id={self.id}, user_id={self.user_id}, subject={self.detected_subject})>"


class Payment(Base):
    """Payment model for storing payment transactions."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Payment details
    amount: Mapped[int] = mapped_column()  # Amount in smallest units
    currency: Mapped[str] = mapped_column()  # XTR or RUB
    provider: Mapped[PaymentProvider] = mapped_column(Enum(PaymentProvider))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING
    )

    # Package info
    package_type: Mapped[PackageType] = mapped_column(Enum(PackageType))
    requests_amount: Mapped[int] = mapped_column(default=0)  # Number of requests in package

    # Provider IDs
    provider_payment_id: Mapped[Optional[str]] = mapped_column(nullable=True, index=True)
    telegram_payment_charge_id: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, user_id={self.user_id}, amount={self.amount}, status={self.status})>"


class Subscription(Base):
    """Subscription model for storing active subscriptions."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Subscription status
    is_active: Mapped[bool] = mapped_column(default=True)
    expires_at: Mapped[datetime] = mapped_column()

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscriptions")
    payment: Mapped[Optional["Payment"]] = relationship()

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
