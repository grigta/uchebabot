"""Utils module for EduHelper Bot."""

from bot.utils.prompts import INTERVIEW_PROMPT, MAIN_PROMPT, PLAN_PROMPT
from bot.utils.text_utils import split_message

__all__ = [
    "MAIN_PROMPT",
    "INTERVIEW_PROMPT",
    "PLAN_PROMPT",
    "split_message",
]
