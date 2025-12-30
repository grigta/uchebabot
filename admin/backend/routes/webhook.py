"""Webhook routes for payment providers."""

from fastapi import APIRouter, Request, Response

from bot.database import async_session
from bot.services.payment_service import PaymentService
from bot.services.yookassa_service import YooKassaService

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/yookassa")
async def yookassa_webhook(request: Request) -> Response:
    """
    Handle YooKassa webhook notifications.

    YooKassa sends notifications about payment status changes.
    We need to process payment.succeeded and payment.canceled events.
    """
    try:
        # Parse webhook data
        webhook_data = await request.json()
    except Exception:
        return Response(status_code=400, content="Invalid JSON")

    # Log webhook for debugging
    event = webhook_data.get("event", "unknown")
    payment_id = webhook_data.get("object", {}).get("id", "unknown")
    print(f"YooKassa webhook: {event} for payment {payment_id}")

    async with async_session() as session:
        payment_service = PaymentService(session)
        yookassa_service = YooKassaService(payment_service)

        try:
            success = await yookassa_service.handle_webhook(webhook_data)
            if success:
                return Response(status_code=200, content="OK")
            else:
                return Response(status_code=400, content="Failed to process webhook")
        except Exception as e:
            print(f"Webhook processing error: {e}")
            # Return 200 anyway to prevent YooKassa from retrying
            # We should log and investigate manually
            return Response(status_code=200, content="OK")


@router.get("/yookassa/test")
async def test_webhook() -> dict:
    """Test endpoint to verify webhook is accessible."""
    return {"status": "ok", "message": "YooKassa webhook is ready"}
