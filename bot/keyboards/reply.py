"""Reply keyboards for EduHelper Bot."""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Get main reply keyboard with Profile and Help buttons."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Профиль"),
                KeyboardButton(text="❓ Помощь"),
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Отправь вопрос или фото задачи...",
    )
