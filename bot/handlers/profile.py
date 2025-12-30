"""Profile handler for user statistics."""

from aiogram import F, Router
from aiogram.types import Message

from bot.database import async_session
from bot.keyboards.inline import get_profile_keyboard
from bot.services import UserService
from bot.services.payment_service import PaymentService
from bot.utils.text_utils import format_tokens

router = Router(name="profile")


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message) -> None:
    """Show user profile with statistics."""
    async with async_session() as session:
        user_service = UserService(session)
        payment_service = PaymentService(session)

        stats = await user_service.get_user_stats(message.from_user.id)
        subscription = await payment_service.get_user_subscription(
            message.from_user.id
        )

    if not stats:
        await message.answer("❌ Профиль не найден. Отправь /start для начала.")
        return

    # Format created_at date
    created_date = stats["created_at"].strftime("%d %B %Y")

    # Format favorite subject
    favorite = stats["favorite_subject"] or "Ещё не определён"

    profile_text = (
        "👤 **Твой профиль**\n\n"
        "📊 **Статистика:**\n"
        f"• Запросов сегодня: {stats['daily_requests']}/{stats['daily_limit']}\n"
    )

    # Add bonus requests info
    if stats.get("bonus_requests", 0) > 0:
        profile_text += f"• Бонусных запросов: {stats['bonus_requests']} 💎\n"

    # Add subscription info
    if subscription:
        profile_text += f"• Подписка до: {subscription.strftime('%d.%m.%Y')} ✨\n"

    profile_text += (
        f"• Всего запросов: {stats['total_requests']}\n"
        f"• Токенов использовано: {format_tokens(stats['total_tokens'])}\n"
        f"• Любимый предмет: {favorite}\n\n"
        f"🗓 С нами с: {created_date}"
    )

    if stats["is_banned"]:
        profile_text += "\n\n🚫 **Статус:** Заблокирован"

    await message.answer(
        profile_text,
        parse_mode="Markdown",
        reply_markup=get_profile_keyboard(),
    )
