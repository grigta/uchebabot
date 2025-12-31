"""Question handler - main task processing flow."""

import asyncio
import base64
import logging
from typing import Any, Optional

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import async_session
from bot.handlers.states import TaskFlow
from bot.keyboards import (
    get_interview_keyboard,
    get_interview_options_keyboard,
    get_main_keyboard,
    get_plan_keyboard,
    get_solution_keyboard,
)
from bot.config import settings
from bot.services import ModerationService, UserService
from bot.services.moderation import moderation_service
from bot.services.openrouter import openrouter_client
from bot.utils.prompts import INTERVIEW_PROMPT, MAIN_PROMPT, PLAN_PROMPT
from bot.utils.text_utils import (
    extract_interview_options,
    extract_subject,
    remove_subject_tag,
    sanitize_markdown,
    should_skip_interview,
    split_message,
)

from aiogram.exceptions import TelegramBadRequest

router = Router(name="question")
logger = logging.getLogger(__name__)

# Timeout for plan confirmation (5 minutes)
PLAN_TIMEOUT = 5 * 60


async def safe_send_message(
    message: Message,
    text: str,
    reply_markup=None,
) -> None:
    """Send message with Markdown, fallback to plain text on error."""
    # First try with sanitized Markdown
    sanitized = sanitize_markdown(text)
    try:
        await message.answer(
            sanitized,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e):
            # Fallback to plain text
            logger.warning(f"Markdown parse failed, sending as plain text: {e}")
            await message.answer(
                text,
                parse_mode=None,
                reply_markup=reply_markup,
            )
        else:
            raise


async def get_image_base64(message: Message, bot: Bot) -> Optional[str]:
    """Download and encode image from message."""
    if not message.photo:
        return None

    # Get largest photo
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)

    return base64.b64encode(file_bytes.read()).decode("utf-8")


async def get_voice_base64(message: Message, bot: Bot) -> Optional[str]:
    """Download and encode voice message (OGG format)."""
    if not message.voice:
        return None

    voice = message.voice
    file = await bot.get_file(voice.file_id)
    file_bytes = await bot.download_file(file.file_path)

    return base64.b64encode(file_bytes.read()).decode("utf-8")


@router.message(F.photo | F.voice | (F.text & ~F.text.startswith("/")))
async def handle_question(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle incoming question (text, photo, or voice)."""
    # Skip if it's a button press
    if message.text in ["👤 Профиль", "❓ Помощь"]:
        return

    # Get question text
    question_text = message.caption if message.photo else message.text

    # For voice messages, use default prompt
    if message.voice and not question_text:
        question_text = "Расшифруй голосовое сообщение и помоги с вопросом"
    elif not question_text:
        question_text = "Помоги решить задачу на фото"

    # Check message length
    if len(question_text) > 4000:
        await message.answer(
            f"📝 Сократи вопрос до 4000 символов. Сейчас: {len(question_text)}"
        )
        return

    # Moderation check
    mod_result = moderation_service.check_content(question_text)
    if not mod_result.is_allowed:
        await message.answer(moderation_service.get_block_message(mod_result.reason))
        return

    # Check user limits
    async with async_session() as session:
        user_service = UserService(session)
        can_request, error_msg, request_type = await user_service.check_can_make_request(
            message.from_user.id
        )

    if not can_request:
        await message.answer(error_msg)
        return

    # Store request type for later use
    await state.update_data(request_type=request_type)

    # Get image if present
    image_base64 = await get_image_base64(message, bot) if message.photo else None

    # Get voice and transcribe if present
    had_voice = False
    transcription_tokens = {"prompt": 0, "completion": 0, "cost": 0.0}
    if message.voice:
        had_voice = True
        await bot.send_chat_action(message.chat.id, "typing")

        voice_base64 = await get_voice_base64(message, bot)
        if voice_base64:
            # Transcribe voice using Gemini 2.5 Flash
            transcription_result = await openrouter_client.transcribe_voice(voice_base64)
            if transcription_result:
                # Prepend transcription to question
                question_text = f"[Голосовое сообщение]: {transcription_result['text']}"
                # Save transcription tokens for cost tracking
                transcription_tokens = {
                    "prompt": transcription_result["prompt_tokens"],
                    "completion": transcription_result["completion_tokens"],
                    "cost": transcription_result["cost_usd"],
                }
            else:
                await message.answer(
                    "Не удалось распознать голосовое сообщение. Попробуй ещё раз или напиши текстом."
                )
                return

    # Store data in state
    await state.update_data(
        question=question_text,
        image_base64=image_base64,
        had_image=bool(image_base64),
        had_voice=had_voice,
        transcription_prompt_tokens=transcription_tokens["prompt"],
        transcription_completion_tokens=transcription_tokens["completion"],
        transcription_cost_usd=transcription_tokens["cost"],
    )

    # Show typing indicator
    await bot.send_chat_action(message.chat.id, "typing")

    # Ask AI for interview questions (voice already transcribed to text)
    try:
        response = await openrouter_client.ask_question(
            question=question_text,
            system_prompt=INTERVIEW_PROMPT,
            image_base64=image_base64,
        )

        interview_response = response["content"]

        # Track tokens from interview stage
        await state.update_data(
            accumulated_prompt_tokens=response["prompt_tokens"],
            accumulated_completion_tokens=response["completion_tokens"],
        )

        # Check if we should skip interview
        if should_skip_interview(interview_response):
            # Skip to plan generation
            await generate_and_show_plan(message, state, bot)
            return

        # Extract options if present
        clean_text, options = extract_interview_options(interview_response)

        # Store interview data
        await state.update_data(interview_question=clean_text)
        await state.set_state(TaskFlow.interview)

        # Send interview question
        if options:
            await message.answer(
                clean_text,
                reply_markup=get_interview_options_keyboard(options),
            )
        else:
            await message.answer(
                clean_text,
                reply_markup=get_interview_keyboard(),
            )

    except Exception as e:
        logger.error(f"Error in interview generation: {e}")
        await message.answer(
            "🔧 Сервис временно недоступен. Попробуй через минуту.",
            reply_markup=get_main_keyboard(),
        )


@router.message(TaskFlow.interview)
async def handle_interview_answer(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    """Handle user's answer to interview question."""
    data = await state.get_data()

    # Update context with interview answer
    interview_context = data.get("interview_context", [])
    interview_context.append(
        {"role": "assistant", "content": data.get("interview_question", "")}
    )
    interview_context.append({"role": "user", "content": message.text})

    await state.update_data(interview_context=interview_context)

    # Generate plan
    await generate_and_show_plan(message, state, bot)


@router.callback_query(F.data.startswith("interview_opt_"))
async def handle_interview_option(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    """Handle interview option selection."""
    # Get option text from button
    option_idx = int(callback.data.replace("interview_opt_", ""))
    option_text = callback.message.reply_markup.inline_keyboard[option_idx][0].text

    data = await state.get_data()

    # Update context with interview answer
    interview_context = data.get("interview_context", [])
    interview_context.append(
        {"role": "assistant", "content": data.get("interview_question", "")}
    )
    interview_context.append({"role": "user", "content": option_text})

    await state.update_data(interview_context=interview_context)
    await callback.answer()

    # Remove keyboard and generate plan
    await callback.message.edit_reply_markup(reply_markup=None)
    await generate_and_show_plan(callback.message, state, bot)


@router.callback_query(F.data == "interview_skip")
async def handle_interview_skip(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    """Handle skip interview button."""
    await callback.answer("Пропускаю интервью...")
    await callback.message.edit_reply_markup(reply_markup=None)

    # Go directly to solving
    await state.update_data(skip_plan=True)
    await solve_task(callback.message, state, bot)


@router.callback_query(F.data == "interview_cancel")
async def handle_interview_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle cancel during interview."""
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "❌ Запрос отменён. Отправь новый вопрос когда будешь готов.",
        reply_markup=get_main_keyboard(),
    )


async def generate_and_show_plan(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    """Generate and show solution plan."""
    await bot.send_chat_action(message.chat.id, "typing")

    data = await state.get_data()
    question = data.get("question", "")
    image_base64 = data.get("image_base64")
    interview_context = data.get("interview_context", [])

    # Build context for plan generation
    context = [{"role": "user", "content": question}]
    context.extend(interview_context)

    try:
        response = await openrouter_client.ask_question(
            question="Составь план решения этой задачи",
            system_prompt=PLAN_PROMPT,
            image_base64=image_base64,
            context=context,
        )

        plan = response["content"]

        # Accumulate tokens from plan stage
        accumulated_prompt = data.get("accumulated_prompt_tokens", 0)
        accumulated_completion = data.get("accumulated_completion_tokens", 0)
        await state.update_data(
            plan=plan,
            accumulated_prompt_tokens=accumulated_prompt + response["prompt_tokens"],
            accumulated_completion_tokens=accumulated_completion + response["completion_tokens"],
        )
        await state.set_state(TaskFlow.awaiting_plan)

        # Send plan with safe Markdown handling
        plan_text = plan + "\n\nПодтвердить план?"
        sanitized_plan = sanitize_markdown(plan_text)
        try:
            await message.answer(
                sanitized_plan,
                reply_markup=get_plan_keyboard(),
                parse_mode="Markdown",
            )
        except TelegramBadRequest as e:
            if "can't parse entities" in str(e):
                await message.answer(
                    plan_text,
                    reply_markup=get_plan_keyboard(),
                    parse_mode=None,
                )
            else:
                raise

        # Start timeout for plan confirmation
        asyncio.create_task(plan_timeout(message.chat.id, state, bot))

    except Exception as e:
        logger.error(f"Error in plan generation: {e}")
        await message.answer(
            "🔧 Сервис временно недоступен. Попробуй через минуту.",
            reply_markup=get_main_keyboard(),
        )
        await state.clear()


async def plan_timeout(chat_id: int, state: FSMContext, bot: Bot) -> None:
    """Handle plan confirmation timeout."""
    await asyncio.sleep(PLAN_TIMEOUT)

    current_state = await state.get_state()
    if current_state == TaskFlow.awaiting_plan.state:
        await state.clear()
        await bot.send_message(
            chat_id,
            "⏱️ Время на подтверждение плана истекло. Отправь задачу заново.",
            reply_markup=get_main_keyboard(),
        )


@router.callback_query(F.data == "plan_confirm")
async def handle_plan_confirm(
    callback: CallbackQuery, state: FSMContext, bot: Bot
) -> None:
    """Handle plan confirmation."""
    await callback.answer("Решаю задачу...")
    await callback.message.edit_reply_markup(reply_markup=None)
    await solve_task(callback.message, state, bot)


@router.callback_query(F.data == "plan_modify")
async def handle_plan_modify(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle plan modification request."""
    await state.set_state(TaskFlow.modifying_plan)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✏️ Напиши, что нужно изменить в плане:")


@router.message(TaskFlow.modifying_plan)
async def handle_plan_modification(
    message: Message, state: FSMContext, bot: Bot
) -> None:
    """Handle plan modification text."""
    data = await state.get_data()

    # Add modification to context
    interview_context = data.get("interview_context", [])
    interview_context.append(
        {"role": "user", "content": f"Измени план: {message.text}"}
    )

    await state.update_data(interview_context=interview_context)

    # Regenerate plan
    await generate_and_show_plan(message, state, bot)


@router.callback_query(F.data == "plan_cancel")
async def handle_plan_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle plan cancellation."""
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "❌ Запрос отменён. Отправь новый вопрос когда будешь готов.",
        reply_markup=get_main_keyboard(),
    )


async def solve_task(message: Message, state: FSMContext, bot: Bot) -> None:
    """Generate final solution."""
    await state.set_state(TaskFlow.processing)
    await bot.send_chat_action(message.chat.id, "typing")

    data = await state.get_data()
    question = data.get("question", "")
    image_base64 = data.get("image_base64")
    interview_context = data.get("interview_context", [])
    plan = data.get("plan", "")
    had_image = data.get("had_image", False)
    had_voice = data.get("had_voice", False)
    skip_plan = data.get("skip_plan", False)
    request_type = data.get("request_type", "daily")

    # Build context
    context = [{"role": "user", "content": question}]
    context.extend(interview_context)

    if plan and not skip_plan:
        context.append({"role": "assistant", "content": f"План решения:\n{plan}"})
        context.append({"role": "user", "content": "Отлично, теперь реши задачу по этому плану"})

    try:
        response = await openrouter_client.ask_question(
            question="Реши задачу подробно, с объяснением каждого шага",
            system_prompt=MAIN_PROMPT,
            image_base64=image_base64,
            context=context,
        )

        answer = response["content"]

        # Extract and remove subject tag
        detected_subject = extract_subject(answer)
        clean_answer = remove_subject_tag(answer)

        # Calculate total tokens from all stages (transcription + interview + plan + solution)
        accumulated_prompt = data.get("accumulated_prompt_tokens", 0)
        accumulated_completion = data.get("accumulated_completion_tokens", 0)

        # Include transcription tokens (from Gemini 2.5 Flash)
        transcription_prompt = data.get("transcription_prompt_tokens", 0)
        transcription_completion = data.get("transcription_completion_tokens", 0)
        transcription_cost = data.get("transcription_cost_usd", 0.0)

        total_prompt_tokens = accumulated_prompt + response["prompt_tokens"] + transcription_prompt
        total_completion_tokens = accumulated_completion + response["completion_tokens"] + transcription_completion
        total_all_tokens = total_prompt_tokens + total_completion_tokens

        # Calculate cost in USD (main model + transcription)
        cost_usd = (
            total_prompt_tokens * settings.openrouter_input_price +
            total_completion_tokens * settings.openrouter_output_price +
            transcription_cost  # Add transcription cost from API response
        )

        # Save request and update usage
        async with async_session() as session:
            user_service = UserService(session)
            request_id = await user_service.increment_usage(
                telegram_id=message.chat.id,
                tokens=response["total_tokens"],
                question=question,
                answer=clean_answer,
                model=response["model"],
                request_type=request_type,
                prompt_tokens=response["prompt_tokens"],
                completion_tokens=response["completion_tokens"],
                response_time_ms=response["response_time_ms"],
                detected_subject=detected_subject,
                had_image=had_image,
                had_voice=had_voice,
                # New fields for aggregated stats
                total_prompt_tokens=total_prompt_tokens,
                total_completion_tokens=total_completion_tokens,
                total_all_tokens=total_all_tokens,
                cost_usd=cost_usd,
            )

        # If Mini App is configured, show WebApp button instead of text
        if settings.webapp_url and request_id:
            await message.answer(
                "✅ Решение готово! Нажми кнопку, чтобы открыть.",
                reply_markup=get_solution_keyboard(request_id),
            )
        else:
            # Fallback: send text directly (if Mini App not configured)
            chunks = split_message(clean_answer)
            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:
                    await safe_send_message(
                        message, chunk, reply_markup=get_main_keyboard()
                    )
                else:
                    await safe_send_message(message, chunk)

    except Exception as e:
        logger.error(f"Error in task solving: {e}")
        await message.answer(
            "🔧 Сервис временно недоступен. Попробуй через минуту.\n"
            "Запрос не был списан с лимита.",
            reply_markup=get_main_keyboard(),
        )

    finally:
        await state.clear()


@router.callback_query(F.data == "cancel")
async def handle_global_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle global cancel callback."""
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "❌ Отменено. Отправь новый вопрос.",
        reply_markup=get_main_keyboard(),
    )
