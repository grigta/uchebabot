"""User service for business logic related to users."""

from datetime import date, datetime, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.repositories import (
    RequestRepository,
    SubscriptionRepository,
    UserRepository,
)

# Moscow timezone for daily reset
MSK = ZoneInfo("Europe/Moscow")


class UserService:
    """Service for user-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.request_repo = RequestRepository(session)
        self.subscription_repo = SubscriptionRepository(session)

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ):
        """Get existing user or create new one."""
        user, created = await self.user_repo.get_or_create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        await self.session.commit()
        return user, created

    async def check_can_make_request(
        self, telegram_id: int
    ) -> Tuple[bool, str, str]:
        """
        Check if user can make a request.

        Returns:
            tuple(can_request, error_message, request_type)
            request_type: "subscription", "bonus", "daily"
        """
        user = await self.user_repo.get_by_telegram_id(telegram_id)

        if not user:
            return False, "Пользователь не найден", ""

        if user.is_banned:
            return False, "🚫 Твой аккаунт заблокирован. Обратись в поддержку.", ""

        # Check if daily requests need reset (Moscow midnight)
        await self._check_daily_reset(user)

        # 1. Check active subscription - unlimited access
        subscription = await self.subscription_repo.get_active(user.id)
        if subscription:
            return True, "", "subscription"

        # 2. Check bonus requests
        if user.bonus_requests > 0:
            return True, "", "bonus"

        # 3. Check daily limit
        limit = user.custom_daily_limit or settings.daily_request_limit

        if user.daily_requests >= limit:
            return (
                False,
                f"⏳ Ты использовал все запросы на сегодня ({limit}/{limit}). "
                "Лимит обновится в 00:00 МСК.\n\n"
                "💎 Купи дополнительные запросы в профиле!",
                "",
            )

        return True, "", "daily"

    async def _check_daily_reset(self, user) -> None:
        """Reset daily requests if it's a new day in Moscow."""
        now_msk = datetime.now(MSK)
        today_msk = now_msk.date()

        if user.last_request_date:
            # Convert last request date to Moscow timezone
            last_date_msk = user.last_request_date.date()

            if last_date_msk < today_msk:
                user.daily_requests = 0
                await self.session.commit()

    async def increment_usage(
        self,
        telegram_id: int,
        tokens: int,
        question: str,
        answer: str,
        model: str,
        request_type: str = "daily",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        response_time_ms: int = 0,
        detected_subject: Optional[str] = None,
        had_image: bool = False,
        # Aggregated stats from all stages (interview + plan + solution)
        total_prompt_tokens: int = 0,
        total_completion_tokens: int = 0,
        total_all_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> Optional[int]:
        """Increment user's usage counters and save request. Returns request ID."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None

        # Handle different request types
        if request_type == "bonus":
            # Use bonus request
            await self.user_repo.use_bonus_request(user.id)
        elif request_type == "daily":
            # Increment daily counters
            await self.user_repo.increment_requests(user.id, tokens)
        # For subscription, we don't decrement anything

        # Always increment total counters and tokens
        user.total_requests += 1
        user.total_tokens += total_all_tokens if total_all_tokens > 0 else tokens
        user.total_cost_usd += cost_usd
        user.last_request_date = datetime.utcnow()

        # Save request record
        request = await self.request_repo.create(
            user_id=user.id,
            question=question,
            answer=answer,
            model_used=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=tokens,
            response_time_ms=response_time_ms,
            detected_subject=detected_subject,
            had_image=had_image,
            # Aggregated stats
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
            total_all_tokens=total_all_tokens,
            cost_usd=cost_usd,
        )

        await self.session.commit()
        return request.id

    async def get_user_stats(self, telegram_id: int) -> Optional[dict]:
        """Get user statistics for profile display."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None

        # Check daily reset
        await self._check_daily_reset(user)

        # Get favorite subject
        favorite_subject = await self.request_repo.get_user_favorite_subject(user.id)

        limit = user.custom_daily_limit or settings.daily_request_limit

        return {
            "daily_requests": user.daily_requests,
            "daily_limit": limit,
            "bonus_requests": user.bonus_requests,
            "total_requests": user.total_requests,
            "total_tokens": user.total_tokens,
            "favorite_subject": favorite_subject,
            "created_at": user.created_at,
            "is_banned": user.is_banned,
        }

    async def ban_user(self, telegram_id: int) -> bool:
        """Ban a user."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        await self.user_repo.set_banned(user.id, True)
        await self.session.commit()
        return True

    async def unban_user(self, telegram_id: int) -> bool:
        """Unban a user."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        await self.user_repo.set_banned(user.id, False)
        await self.session.commit()
        return True

    async def set_custom_limit(self, telegram_id: int, limit: Optional[int]) -> bool:
        """Set custom daily limit for user."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False
        await self.user_repo.set_custom_limit(user.id, limit)
        await self.session.commit()
        return True
