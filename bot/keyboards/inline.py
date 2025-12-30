"""Inline keyboards for EduHelper Bot."""

from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.models import PackageType
from bot.services.payment_service import Package, PaymentService


def get_guide_keyboard(step: int) -> InlineKeyboardMarkup:
    """Get keyboard for guide steps."""
    if step < 3:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Далее →", callback_data=f"guide_{step + 1}")]
            ]
        )
    else:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✨ Понятно, начнём!", callback_data="guide_finish"
                    )
                ]
            ]
        )


def get_interview_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for interview step with skip option."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏭ Пропустить и решить сразу",
                    callback_data="interview_skip",
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="interview_cancel")],
        ]
    )


def get_interview_options_keyboard(options: List[str]) -> InlineKeyboardMarkup:
    """Get keyboard with interview answer options."""
    buttons = [
        [InlineKeyboardButton(text=opt, callback_data=f"interview_opt_{i}")]
        for i, opt in enumerate(options)
    ]
    buttons.append(
        [
            InlineKeyboardButton(
                text="⏭ Пропустить и решить сразу",
                callback_data="interview_skip",
            )
        ]
    )
    buttons.append(
        [InlineKeyboardButton(text="❌ Отмена", callback_data="interview_cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_plan_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for plan confirmation."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, решай", callback_data="plan_confirm"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="plan_modify"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="plan_cancel")],
        ]
    )


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Get simple cancel keyboard."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for profile with buy button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎 Купить запросы",
                    callback_data="buy_requests",
                )
            ]
        ]
    )


def get_packages_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard with available packages."""
    packages = PaymentService.get_packages()
    buttons = []

    for package in packages:
        if package.is_subscription:
            text = f"∞ {package.name} — {package.price_stars}⭐ / {package.price_rub_display}₽"
        else:
            text = f"{package.name} — {package.price_stars}⭐ / {package.price_rub_display}₽"

        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"package:{package.type.value}",
            )
        ])

    # Add back button
    buttons.append([
        InlineKeyboardButton(text="← Назад", callback_data="back_to_profile")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_methods_keyboard(package_type: str) -> InlineKeyboardMarkup:
    """Get keyboard with payment methods for selected package."""
    package = PaymentService.get_package_by_type(PackageType(package_type))
    if not package:
        return get_packages_keyboard()

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⭐ Telegram Stars ({package.price_stars} Stars)",
                    callback_data=f"pay:stars:{package_type}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💳 Карта / СБП ({package.price_rub_display} ₽)",
                    callback_data=f"pay:yookassa:{package_type}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data="buy_requests",
                )
            ],
        ]
    )
