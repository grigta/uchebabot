"""Payment handlers for EduHelper Bot."""

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery

from bot.config import settings
from bot.database import async_session
from bot.database.models import PackageType
from bot.keyboards.inline import (
    get_packages_keyboard,
    get_payment_methods_keyboard,
    get_profile_keyboard,
)
from bot.services.payment_service import PaymentService
from bot.services.telegram_stars import TelegramStarsService
from bot.services.yookassa_service import YooKassaService

router = Router(name="payment")


@router.callback_query(F.data == "buy_requests")
async def show_packages(callback: CallbackQuery) -> None:
    """Show available packages for purchase."""
    await callback.message.edit_text(
        "💎 **Выберите пакет:**\n\n"
        "Бонусные запросы не сгорают и могут использоваться в любое время.\n"
        "Подписка даёт безлимитный доступ на 30 дней.",
        reply_markup=get_packages_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery) -> None:
    """Go back to profile from packages."""
    async with async_session() as session:
        payment_service = PaymentService(session)
        subscription = await payment_service.get_user_subscription(
            callback.from_user.id
        )
        bonus_requests = await payment_service.get_user_bonus_requests(
            callback.from_user.id
        )

    # Build profile text with payment info
    profile_lines = ["👤 **Твой профиль**\n"]

    if bonus_requests > 0:
        profile_lines.append(f"💎 Бонусных запросов: {bonus_requests}")

    if subscription:
        profile_lines.append(
            f"✨ Подписка до: {subscription.strftime('%d.%m.%Y')}"
        )

    await callback.message.edit_text(
        "\n".join(profile_lines),
        reply_markup=get_profile_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("package:"))
async def select_package(callback: CallbackQuery) -> None:
    """Handle package selection, show payment methods."""
    package_type = callback.data.split(":")[1]

    try:
        PackageType(package_type)  # Validate package type
    except ValueError:
        await callback.answer("Неизвестный пакет", show_alert=True)
        return

    package = PaymentService.get_package_by_type(PackageType(package_type))
    if not package:
        await callback.answer("Пакет не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"💳 **Способ оплаты для: {package.name}**\n\n"
        "Выберите удобный способ оплаты:",
        reply_markup=get_payment_methods_keyboard(package_type),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:stars:"))
async def pay_with_stars(callback: CallbackQuery, bot: Bot) -> None:
    """Handle Telegram Stars payment."""
    package_type_str = callback.data.split(":")[2]

    try:
        package_type = PackageType(package_type_str)
    except ValueError:
        await callback.answer("Неизвестный пакет", show_alert=True)
        return

    async with async_session() as session:
        payment_service = PaymentService(session)
        stars_service = TelegramStarsService(bot, payment_service)

        payment_id = await stars_service.send_invoice(
            chat_id=callback.message.chat.id,
            package_type=package_type,
            telegram_id=callback.from_user.id,
        )

        if not payment_id:
            await callback.answer(
                "Ошибка создания платежа. Попробуйте позже.",
                show_alert=True,
            )
            return

    await callback.answer()
    # Delete the selection message
    await callback.message.delete()


@router.callback_query(F.data.startswith("pay:yookassa:"))
async def pay_with_yookassa(callback: CallbackQuery) -> None:
    """Handle YooKassa payment."""
    package_type_str = callback.data.split(":")[2]

    try:
        package_type = PackageType(package_type_str)
    except ValueError:
        await callback.answer("Неизвестный пакет", show_alert=True)
        return

    # Check if YooKassa is configured
    if not settings.yookassa_shop_id or settings.yookassa_shop_id == "your_shop_id":
        await callback.answer(
            "Оплата картой временно недоступна. Используйте Telegram Stars.",
            show_alert=True,
        )
        return

    async with async_session() as session:
        payment_service = PaymentService(session)
        yookassa_service = YooKassaService(payment_service)

        # Get bot username for return URL
        bot_info = await callback.bot.get_me()
        return_url = f"https://t.me/{bot_info.username}"

        result = await yookassa_service.create_payment(
            telegram_id=callback.from_user.id,
            package_type=package_type,
            return_url=return_url,
        )

        if not result:
            await callback.answer(
                "Ошибка создания платежа. Попробуйте позже.",
                show_alert=True,
            )
            return

    # Send payment link
    await callback.message.edit_text(
        "💳 **Оплата через YooKassa**\n\n"
        f"Нажмите на кнопку ниже для перехода к оплате.\n"
        f"После оплаты запросы будут начислены автоматически.",
        reply_markup={
            "inline_keyboard": [
                [{"text": "💳 Перейти к оплате", "url": result["payment_url"]}],
                [{"text": "← Назад", "callback_data": "buy_requests"}],
            ]
        },
        parse_mode="Markdown",
    )
    await callback.answer()


@router.pre_checkout_query()
async def handle_pre_checkout(
    pre_checkout_query: PreCheckoutQuery, bot: Bot
) -> None:
    """Handle pre-checkout query for Telegram Stars."""
    async with async_session() as session:
        payment_service = PaymentService(session)
        stars_service = TelegramStarsService(bot, payment_service)
        await stars_service.handle_pre_checkout(pre_checkout_query)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message, bot: Bot) -> None:
    """Handle successful Telegram Stars payment."""
    if not message.successful_payment:
        return

    async with async_session() as session:
        payment_service = PaymentService(session)
        stars_service = TelegramStarsService(bot, payment_service)

        success = await stars_service.handle_successful_payment(
            message.successful_payment
        )

        if success:
            # Get updated info
            bonus_requests = await payment_service.get_user_bonus_requests(
                message.from_user.id
            )
            subscription = await payment_service.get_user_subscription(
                message.from_user.id
            )

            if subscription:
                await message.answer(
                    "✅ **Оплата прошла успешно!**\n\n"
                    f"✨ Подписка активирована до {subscription.strftime('%d.%m.%Y')}.\n"
                    "Теперь у вас безлимитный доступ!",
                    parse_mode="Markdown",
                )
            else:
                await message.answer(
                    "✅ **Оплата прошла успешно!**\n\n"
                    f"💎 Ваш баланс: {bonus_requests} бонусных запросов.\n"
                    "Они не сгорают и могут использоваться в любое время.",
                    parse_mode="Markdown",
                )
        else:
            await message.answer(
                "❌ Произошла ошибка при обработке платежа. "
                "Обратитесь в поддержку."
            )
