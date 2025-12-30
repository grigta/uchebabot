"""Telegram Stars payment service."""

from typing import Optional

from aiogram import Bot
from aiogram.types import LabeledPrice, PreCheckoutQuery, SuccessfulPayment

from bot.database.models import PackageType, PaymentProvider
from bot.services.payment_service import PaymentService


class TelegramStarsService:
    """Service for Telegram Stars payments."""

    def __init__(self, bot: Bot, payment_service: PaymentService):
        self.bot = bot
        self.payment_service = payment_service

    async def send_invoice(
        self,
        chat_id: int,
        package_type: PackageType,
        telegram_id: int,
    ) -> Optional[int]:
        """
        Send invoice for Telegram Stars payment.

        Returns payment_id if successful, None otherwise.
        """
        package = PaymentService.get_package_by_type(package_type)
        if not package:
            return None

        # Create payment record
        payment = await self.payment_service.create_payment(
            telegram_id=telegram_id,
            package_type=package_type,
            provider=PaymentProvider.TELEGRAM_STARS,
        )

        if not payment:
            return None

        # Prepare invoice data
        title = f"{package.name}"
        description = (
            f"Покупка пакета: {package.name}"
            if not package.is_subscription
            else "Безлимитный доступ на 30 дней"
        )

        # Payload contains payment_id for later reference
        payload = f"payment:{payment.id}"

        prices = [
            LabeledPrice(label=package.name, amount=package.price_stars)
        ]

        # Send invoice with Telegram Stars
        await self.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            currency="XTR",  # Telegram Stars currency
            prices=prices,
            provider_token="",  # Empty for Telegram Stars
        )

        return payment.id

    async def handle_pre_checkout(
        self, pre_checkout_query: PreCheckoutQuery
    ) -> bool:
        """
        Handle pre-checkout query.

        Returns True if payment can proceed, False otherwise.
        """
        # Extract payment_id from payload
        payload = pre_checkout_query.invoice_payload
        if not payload.startswith("payment:"):
            await pre_checkout_query.answer(
                ok=False,
                error_message="Invalid payment data",
            )
            return False

        try:
            payment_id = int(payload.split(":")[1])
        except (ValueError, IndexError):
            await pre_checkout_query.answer(
                ok=False,
                error_message="Invalid payment ID",
            )
            return False

        # Verify payment exists and is pending
        payment = await self.payment_service.payment_repo.get_by_id(payment_id)
        if not payment:
            await pre_checkout_query.answer(
                ok=False,
                error_message="Payment not found",
            )
            return False

        # All checks passed - approve the payment
        await pre_checkout_query.answer(ok=True)
        return True

    async def handle_successful_payment(
        self, successful_payment: SuccessfulPayment
    ) -> bool:
        """
        Handle successful payment.

        Returns True if payment was processed successfully.
        """
        # Extract payment_id from payload
        payload = successful_payment.invoice_payload
        if not payload.startswith("payment:"):
            return False

        try:
            payment_id = int(payload.split(":")[1])
        except (ValueError, IndexError):
            return False

        # Process the payment
        return await self.payment_service.process_successful_payment(
            payment_id=payment_id,
            telegram_payment_charge_id=successful_payment.telegram_payment_charge_id,
        )
