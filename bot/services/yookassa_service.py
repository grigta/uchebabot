"""YooKassa payment service."""

import hashlib
import hmac
import uuid
from typing import Any, Dict, Optional

import aiohttp

from bot.config import settings
from bot.database.models import PackageType, PaymentProvider, PaymentStatus
from bot.services.payment_service import PaymentService


class YooKassaService:
    """Service for YooKassa payments."""

    API_URL = "https://api.yookassa.ru/v3"

    def __init__(self, payment_service: PaymentService):
        self.payment_service = payment_service
        self.shop_id = settings.yookassa_shop_id
        self.secret_key = settings.yookassa_secret_key

    def _get_auth(self) -> aiohttp.BasicAuth:
        """Get basic auth for API requests."""
        return aiohttp.BasicAuth(self.shop_id, self.secret_key)

    async def create_payment(
        self,
        telegram_id: int,
        package_type: PackageType,
        return_url: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Create YooKassa payment.

        Returns dict with payment_url and payment_id if successful.
        """
        package = PaymentService.get_package_by_type(package_type)
        if not package:
            return None

        # Create payment record in our database
        payment = await self.payment_service.create_payment(
            telegram_id=telegram_id,
            package_type=package_type,
            provider=PaymentProvider.YOOKASSA,
        )

        if not payment:
            return None

        # Generate idempotence key
        idempotence_key = str(uuid.uuid4())

        # Prepare payment data for YooKassa
        payment_data = {
            "amount": {
                "value": f"{package.price_rub / 100:.2f}",  # Convert kopecks to rubles
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "capture": True,
            "description": f"Покупка: {package.name}",
            "metadata": {
                "payment_id": payment.id,
                "telegram_id": telegram_id,
                "package_type": package_type.value,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.API_URL}/payments",
                    json=payment_data,
                    auth=self._get_auth(),
                    headers={
                        "Idempotence-Key": idempotence_key,
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        print(f"YooKassa error: {error_text}")
                        return None

                    result = await response.json()

                    # Update payment with YooKassa payment ID
                    payment.provider_payment_id = result.get("id")
                    await self.payment_service.session.commit()

                    return {
                        "payment_url": result["confirmation"]["confirmation_url"],
                        "payment_id": payment.id,
                        "yookassa_payment_id": result["id"],
                    }

        except aiohttp.ClientError as e:
            print(f"YooKassa request error: {e}")
            return None

    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Handle YooKassa webhook notification.

        Returns True if webhook was processed successfully.
        """
        event = webhook_data.get("event")
        payment_object = webhook_data.get("object", {})

        if event == "payment.succeeded":
            return await self._handle_payment_succeeded(payment_object)
        elif event == "payment.canceled":
            return await self._handle_payment_canceled(payment_object)

        # Unknown event - just acknowledge
        return True

    async def _handle_payment_succeeded(
        self, payment_object: Dict[str, Any]
    ) -> bool:
        """Handle successful payment webhook."""
        yookassa_payment_id = payment_object.get("id")
        if not yookassa_payment_id:
            return False

        # Find payment by YooKassa ID
        payment = await self.payment_service.get_payment_by_provider_id(
            yookassa_payment_id
        )

        if not payment:
            # Try to get from metadata
            metadata = payment_object.get("metadata", {})
            payment_id = metadata.get("payment_id")
            if payment_id:
                payment = await self.payment_service.payment_repo.get_by_id(
                    int(payment_id)
                )

        if not payment:
            return False

        # Process the payment
        return await self.payment_service.process_successful_payment(
            payment_id=payment.id
        )

    async def _handle_payment_canceled(
        self, payment_object: Dict[str, Any]
    ) -> bool:
        """Handle canceled payment webhook."""
        yookassa_payment_id = payment_object.get("id")
        if not yookassa_payment_id:
            return False

        payment = await self.payment_service.get_payment_by_provider_id(
            yookassa_payment_id
        )

        if not payment:
            return False

        return await self.payment_service.process_failed_payment(payment.id)

    async def get_payment_status(
        self, yookassa_payment_id: str
    ) -> Optional[str]:
        """Get payment status from YooKassa."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_URL}/payments/{yookassa_payment_id}",
                    auth=self._get_auth(),
                ) as response:
                    if response.status != 200:
                        return None

                    result = await response.json()
                    return result.get("status")

        except aiohttp.ClientError:
            return None

    @staticmethod
    def verify_webhook_signature(
        body: bytes,
        signature: str,
        secret: str,
    ) -> bool:
        """
        Verify webhook signature (if using webhook secret).

        Note: YooKassa webhooks typically use IP whitelisting,
        but this method can be used for additional security.
        """
        expected_signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)
