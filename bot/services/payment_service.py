"""Payment service for handling payment business logic."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.models import PackageType, Payment, PaymentProvider, PaymentStatus
from bot.database.repositories import (
    PaymentRepository,
    SubscriptionRepository,
    UserRepository,
)


@dataclass
class Package:
    """Package information for purchase."""

    type: PackageType
    name: str
    requests: int
    price_stars: int
    price_rub: int  # In kopecks
    is_subscription: bool = False

    @property
    def price_rub_display(self) -> str:
        """Get price in rubles for display."""
        return f"{self.price_rub / 100:.0f}"


class PaymentService:
    """Service for payment-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.subscription_repo = SubscriptionRepository(session)

    @staticmethod
    def get_packages() -> List[Package]:
        """Get list of available packages."""
        return [
            Package(
                type=PackageType.REQUESTS_50,
                name="50 запросов",
                requests=50,
                price_stars=settings.price_50_requests_stars,
                price_rub=settings.price_50_requests_rub,
            ),
            Package(
                type=PackageType.REQUESTS_100,
                name="100 запросов",
                requests=100,
                price_stars=settings.price_100_requests_stars,
                price_rub=settings.price_100_requests_rub,
            ),
            Package(
                type=PackageType.SUBSCRIPTION,
                name="Безлимит на месяц",
                requests=0,  # Unlimited
                price_stars=settings.price_subscription_stars,
                price_rub=settings.price_subscription_rub,
                is_subscription=True,
            ),
        ]

    @staticmethod
    def get_package_by_type(package_type: PackageType) -> Optional[Package]:
        """Get package by its type."""
        packages = PaymentService.get_packages()
        for package in packages:
            if package.type == package_type:
                return package
        return None

    async def create_payment(
        self,
        telegram_id: int,
        package_type: PackageType,
        provider: PaymentProvider,
        provider_payment_id: Optional[str] = None,
    ) -> Optional[Payment]:
        """Create a new payment record."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None

        package = self.get_package_by_type(package_type)
        if not package:
            return None

        # Determine amount and currency based on provider
        if provider == PaymentProvider.TELEGRAM_STARS:
            amount = package.price_stars
            currency = "XTR"
        else:
            amount = package.price_rub
            currency = "RUB"

        payment = await self.payment_repo.create(
            user_id=user.id,
            amount=amount,
            currency=currency,
            provider=provider,
            package_type=package_type,
            requests_amount=package.requests,
            provider_payment_id=provider_payment_id,
        )

        await self.session.commit()
        return payment

    async def process_successful_payment(
        self,
        payment_id: int,
        telegram_payment_charge_id: Optional[str] = None,
    ) -> bool:
        """Process a successful payment - add requests or subscription."""
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment or payment.status == PaymentStatus.SUCCEEDED:
            return False

        # Update payment status
        await self.payment_repo.update_status(
            payment_id=payment_id,
            status=PaymentStatus.SUCCEEDED,
            telegram_payment_charge_id=telegram_payment_charge_id,
        )

        package = self.get_package_by_type(payment.package_type)
        if not package:
            return False

        if package.is_subscription:
            # Create or extend subscription
            existing_sub = await self.subscription_repo.get_active(payment.user_id)
            if existing_sub:
                await self.subscription_repo.extend_subscription(payment.user_id, 30)
            else:
                expires_at = datetime.utcnow() + timedelta(days=30)
                await self.subscription_repo.create(
                    user_id=payment.user_id,
                    expires_at=expires_at,
                    payment_id=payment_id,
                )
        else:
            # Add bonus requests
            await self.user_repo.add_bonus_requests(
                payment.user_id, package.requests
            )

        await self.session.commit()
        return True

    async def process_failed_payment(self, payment_id: int) -> bool:
        """Mark payment as failed."""
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment:
            return False

        await self.payment_repo.update_status(
            payment_id=payment_id,
            status=PaymentStatus.FAILED,
        )
        await self.session.commit()
        return True

    async def get_user_subscription(self, telegram_id: int) -> Optional[datetime]:
        """Get user's subscription expiration date if active."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None

        subscription = await self.subscription_repo.get_active(user.id)
        if subscription:
            return subscription.expires_at
        return None

    async def get_user_bonus_requests(self, telegram_id: int) -> int:
        """Get user's bonus requests count."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return 0
        return user.bonus_requests

    async def has_active_subscription(self, telegram_id: int) -> bool:
        """Check if user has active subscription."""
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return False

        subscription = await self.subscription_repo.get_active(user.id)
        return subscription is not None

    async def get_payment_by_provider_id(
        self, provider_payment_id: str
    ) -> Optional[Payment]:
        """Get payment by provider payment ID."""
        return await self.payment_repo.get_by_provider_id(provider_payment_id)
