"""Repository pattern implementations for database operations."""

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models import (
    PackageType,
    Payment,
    PaymentProvider,
    PaymentStatus,
    Request,
    Subscription,
    User,
)


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by database ID."""
        return await self.session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> Tuple[User, bool]:
        """Get existing user or create new one. Returns (user, created)."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            # Update user info if changed
            if username != user.username:
                user.username = username
            if first_name != user.first_name:
                user.first_name = first_name
            if last_name != user.last_name:
                user.last_name = last_name
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user, True

    async def get_with_requests(self, user_id: int) -> Optional[User]:
        """Get user with their requests (eager loading)."""
        result = await self.session.execute(
            select(User).where(User.id == user_id).options(selectinload(User.requests))
        )
        return result.scalar_one_or_none()

    async def increment_requests(self, user_id: int, tokens: int) -> None:
        """Increment user's request counters."""
        user = await self.get_by_id(user_id)
        if user:
            user.daily_requests += 1
            user.total_requests += 1
            user.total_tokens += tokens
            user.last_request_date = datetime.utcnow()

    async def reset_daily_requests(self, user_id: int) -> None:
        """Reset daily request counter for user."""
        user = await self.get_by_id(user_id)
        if user:
            user.daily_requests = 0

    async def set_banned(self, user_id: int, banned: bool) -> None:
        """Set user ban status."""
        user = await self.get_by_id(user_id)
        if user:
            user.is_banned = banned

    async def set_custom_limit(self, user_id: int, limit: Optional[int]) -> None:
        """Set custom daily limit for user."""
        user = await self.get_by_id(user_id)
        if user:
            user.custom_daily_limit = limit

    async def add_bonus_requests(self, user_id: int, amount: int) -> None:
        """Add bonus requests to user."""
        user = await self.get_by_id(user_id)
        if user:
            user.bonus_requests += amount

    async def use_bonus_request(self, user_id: int) -> bool:
        """Use one bonus request. Returns True if successful."""
        user = await self.get_by_id(user_id)
        if user and user.bonus_requests > 0:
            user.bonus_requests -= 1
            return True
        return False

    async def set_onboarding_completed(self, user_id: int) -> None:
        """Mark onboarding as completed for user."""
        user = await self.get_by_id(user_id)
        if user:
            user.onboarding_completed = True

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
    ) -> List[User]:
        """Get all users with pagination and optional search."""
        query = select(User).order_by(User.created_at.desc())

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                (User.username.ilike(search_filter))
                | (User.first_name.ilike(search_filter))
                | (User.last_name.ilike(search_filter))
            )

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, search: Optional[str] = None) -> int:
        """Count total users."""
        query = select(func.count(User.id))
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                (User.username.ilike(search_filter))
                | (User.first_name.ilike(search_filter))
                | (User.last_name.ilike(search_filter))
            )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_active_today(self) -> int:
        """Get count of users active today (DAU)."""
        today = date.today()
        result = await self.session.execute(
            select(func.count(User.id)).where(
                func.date(User.last_request_date) == today
            )
        )
        return result.scalar() or 0

    async def get_active_month(self) -> int:
        """Get count of users active this month (MAU)."""
        month_ago = datetime.utcnow() - timedelta(days=30)
        result = await self.session.execute(
            select(func.count(User.id)).where(User.last_request_date >= month_ago)
        )
        return result.scalar() or 0


class RequestRepository:
    """Repository for Request model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        question: str,
        answer: str,
        model_used: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        response_time_ms: int = 0,
        detected_subject: Optional[str] = None,
        had_image: bool = False,
        had_voice: bool = False,
        # Aggregated stats from all stages
        total_prompt_tokens: int = 0,
        total_completion_tokens: int = 0,
        total_all_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> Request:
        """Create new request record."""
        request = Request(
            user_id=user_id,
            question=question,
            answer=answer,
            model_used=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            response_time_ms=response_time_ms,
            detected_subject=detected_subject,
            had_image=had_image,
            had_voice=had_voice,
            # Aggregated stats
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_all_tokens=total_all_tokens,
            cost_usd=cost_usd,
        )
        self.session.add(request)
        await self.session.flush()
        return request

    async def get_by_id(self, request_id: int) -> Optional[Request]:
        """Get request by ID."""
        return await self.session.get(Request, request_id)

    async def get_by_id_and_telegram_id(
        self, request_id: int, telegram_id: int
    ) -> Optional[Request]:
        """Get request by ID, ensuring it belongs to the user with given telegram_id."""
        result = await self.session.execute(
            select(Request)
            .join(User)
            .where(Request.id == request_id)
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_user_requests_by_telegram_id(
        self,
        telegram_id: int,
        offset: int = 0,
        limit: int = 50,
    ) -> List[Request]:
        """Get requests for a user by their telegram_id."""
        result = await self.session.execute(
            select(Request)
            .join(User)
            .where(User.telegram_id == telegram_id)
            .order_by(Request.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_user_requests_by_telegram_id(self, telegram_id: int) -> int:
        """Count total requests for a user by their telegram_id."""
        result = await self.session.execute(
            select(func.count(Request.id))
            .join(User)
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar() or 0

    async def get_user_requests(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 50,
    ) -> List[Request]:
        """Get requests for a specific user."""
        result = await self.session.execute(
            select(Request)
            .where(Request.user_id == user_id)
            .order_by(Request.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_today(self) -> int:
        """Count requests made today."""
        today = date.today()
        result = await self.session.execute(
            select(func.count(Request.id)).where(
                func.date(Request.created_at) == today
            )
        )
        return result.scalar() or 0

    async def count_week(self) -> int:
        """Count requests made this week."""
        week_ago = datetime.utcnow() - timedelta(days=7)
        result = await self.session.execute(
            select(func.count(Request.id)).where(Request.created_at >= week_ago)
        )
        return result.scalar() or 0

    async def get_popular_subjects(self, limit: int = 10) -> List[dict]:
        """Get most popular detected subjects."""
        result = await self.session.execute(
            select(Request.detected_subject, func.count(Request.id).label("count"))
            .where(Request.detected_subject.is_not(None))
            .group_by(Request.detected_subject)
            .order_by(func.count(Request.id).desc())
            .limit(limit)
        )
        return [
            {"subject": row.detected_subject, "count": row.count}
            for row in result.all()
        ]

    async def get_user_favorite_subject(self, user_id: int) -> Optional[str]:
        """Get user's most used subject."""
        result = await self.session.execute(
            select(Request.detected_subject)
            .where(Request.user_id == user_id)
            .where(Request.detected_subject.is_not(None))
            .group_by(Request.detected_subject)
            .order_by(func.count(Request.id).desc())
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None

    # Cost statistics methods
    async def get_total_cost(self) -> float:
        """Get total cost of all requests in USD."""
        result = await self.session.execute(
            select(func.sum(Request.cost_usd))
        )
        return result.scalar() or 0.0

    async def get_cost_today(self) -> float:
        """Get total cost of requests made today."""
        today = date.today()
        result = await self.session.execute(
            select(func.sum(Request.cost_usd)).where(
                func.date(Request.created_at) == today
            )
        )
        return result.scalar() or 0.0

    async def get_cost_month(self) -> float:
        """Get total cost of requests made this month."""
        month_ago = datetime.utcnow() - timedelta(days=30)
        result = await self.session.execute(
            select(func.sum(Request.cost_usd)).where(
                Request.created_at >= month_ago
            )
        )
        return result.scalar() or 0.0

    async def get_avg_cost_per_request(self) -> float:
        """Get average cost per request in USD."""
        result = await self.session.execute(
            select(func.avg(Request.cost_usd))
        )
        return result.scalar() or 0.0

    async def get_avg_tokens_per_request(self) -> float:
        """Get average total tokens per request."""
        result = await self.session.execute(
            select(func.avg(Request.total_all_tokens))
        )
        return result.scalar() or 0.0


class PaymentRepository:
    """Repository for Payment model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        amount: int,
        currency: str,
        provider: PaymentProvider,
        package_type: PackageType,
        requests_amount: int = 0,
        provider_payment_id: Optional[str] = None,
        status: PaymentStatus = PaymentStatus.PENDING,
    ) -> Payment:
        """Create new payment record."""
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            provider=provider,
            package_type=package_type,
            requests_amount=requests_amount,
            provider_payment_id=provider_payment_id,
            status=status,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID."""
        return await self.session.get(Payment, payment_id)

    async def get_by_provider_id(self, provider_payment_id: str) -> Optional[Payment]:
        """Get payment by provider payment ID."""
        result = await self.session.execute(
            select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_charge_id(self, charge_id: str) -> Optional[Payment]:
        """Get payment by Telegram payment charge ID."""
        result = await self.session.execute(
            select(Payment).where(Payment.telegram_payment_charge_id == charge_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        payment_id: int,
        status: PaymentStatus,
        telegram_payment_charge_id: Optional[str] = None,
    ) -> Optional[Payment]:
        """Update payment status."""
        payment = await self.get_by_id(payment_id)
        if payment:
            payment.status = status
            if telegram_payment_charge_id:
                payment.telegram_payment_charge_id = telegram_payment_charge_id
        return payment

    async def get_user_payments(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 50,
    ) -> List[Payment]:
        """Get payments for a specific user."""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_successful_payments_count(self, user_id: int) -> int:
        """Count successful payments for user."""
        result = await self.session.execute(
            select(func.count(Payment.id))
            .where(Payment.user_id == user_id)
            .where(Payment.status == PaymentStatus.SUCCEEDED)
        )
        return result.scalar() or 0


class SubscriptionRepository:
    """Repository for Subscription model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: int,
        expires_at: datetime,
        payment_id: Optional[int] = None,
    ) -> Subscription:
        """Create new subscription."""
        subscription = Subscription(
            user_id=user_id,
            expires_at=expires_at,
            payment_id=payment_id,
            is_active=True,
        )
        self.session.add(subscription)
        await self.session.flush()
        return subscription

    async def get_active(self, user_id: int) -> Optional[Subscription]:
        """Get active subscription for user."""
        now = datetime.utcnow()
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.is_active == True)
            .where(Subscription.expires_at > now)
            .order_by(Subscription.expires_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, subscription_id: int) -> Optional[Subscription]:
        """Get subscription by ID."""
        return await self.session.get(Subscription, subscription_id)

    async def deactivate(self, subscription_id: int) -> None:
        """Deactivate subscription."""
        subscription = await self.get_by_id(subscription_id)
        if subscription:
            subscription.is_active = False

    async def deactivate_expired(self) -> int:
        """Deactivate all expired subscriptions. Returns count of deactivated."""
        now = datetime.utcnow()
        result = await self.session.execute(
            update(Subscription)
            .where(Subscription.is_active == True)
            .where(Subscription.expires_at <= now)
            .values(is_active=False)
        )
        return result.rowcount

    async def extend_subscription(
        self, user_id: int, days: int = 30
    ) -> Optional[Subscription]:
        """Extend existing subscription or create new one."""
        active_sub = await self.get_active(user_id)
        if active_sub:
            # Extend existing subscription
            active_sub.expires_at = active_sub.expires_at + timedelta(days=days)
            return active_sub
        return None
