"""Start command and guide handlers."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import async_session
from bot.database.repositories import UserRepository
from bot.keyboards import get_guide_keyboard, get_main_keyboard
from bot.services import UserService

router = Router(name="start")

# Guide messages
GUIDE_MESSAGES = [
    (
        "👋 Привет! Я EduHelper — твой помощник в учёбе!\n\n"
        "Я помогу разобраться с любыми задачами:\n"
        "• Математика и физика\n"
        "• Программирование\n"
        "• Языки и литература\n"
        "• И многое другое!"
    ),
    (
        "📸 Отправь задачу любым удобным способом:\n\n"
        "• Текстом — просто напиши условие\n"
        "• Фото — сфоткай задачу из учебника\n"
        "• Голосовым — надиктуй вопрос\n\n"
        "Я задам уточняющие вопросы если нужно, "
        "составлю план решения и подробно объясню."
    ),
    (
        "🎉 Готово!\n\n"
        "Ответы открываются в мини-приложении с красивым "
        "оформлением формул и кода.\n\n"
        "💡 Чем подробнее опишешь задачу — тем лучше смогу помочь!"
    ),
]

WELCOME_BACK_MESSAGE = (
    "👋 С возвращением!\n\n"
    "Отправь задачу — текстом, фото или голосовым сообщением."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command - show interactive guide or welcome back."""
    # Clear any existing state
    await state.clear()

    # Get or create user
    async with async_session() as session:
        user_service = UserService(session)
        user, created = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        # Check if onboarding already completed
        if user.onboarding_completed:
            await message.answer(
                WELCOME_BACK_MESSAGE,
                reply_markup=get_main_keyboard(),
            )
            return

    # Send first guide message for new users
    await message.answer(
        GUIDE_MESSAGES[0],
        reply_markup=get_guide_keyboard(1),
    )


@router.callback_query(F.data.startswith("guide_"))
async def process_guide_callback(callback: CallbackQuery) -> None:
    """Handle guide navigation callbacks."""
    action = callback.data.replace("guide_", "")

    if action == "finish":
        # Mark onboarding as completed
        async with async_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(callback.from_user.id)
            if user:
                await user_repo.set_onboarding_completed(user.id)
                await session.commit()

        # Show main keyboard and finish guide
        await callback.message.edit_text(GUIDE_MESSAGES[2])
        await callback.message.answer(
            "Отправь мне свой вопрос! 📚",
            reply_markup=get_main_keyboard(),
        )
    else:
        # Show next guide step
        step = int(action)
        if step <= len(GUIDE_MESSAGES):
            await callback.message.edit_text(
                GUIDE_MESSAGES[step - 1],
                reply_markup=get_guide_keyboard(step),
            )

    await callback.answer()
