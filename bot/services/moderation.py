"""Content moderation service for filtering inappropriate content."""

import re
from typing import NamedTuple, Optional


class ModerationResult(NamedTuple):
    """Result of content moderation check."""

    is_allowed: bool
    reason: Optional[str] = None


class ModerationService:
    """Service for content moderation and filtering."""

    # Jailbreak patterns to block
    JAILBREAK_PATTERNS = [
        r"забудь\s+(все\s+)?инструкции",
        r"ignore\s+(all\s+)?(previous\s+)?prompt",
        r"ignore\s+(all\s+)?(previous\s+)?instructions",
        r"ты\s+теперь\s+(?!помощник)",
        r"притворись\s+что\s+ты",
        r"act\s+as\s+if\s+you",
        r"pretend\s+(that\s+)?you\s+are",
        r"you\s+are\s+now\s+(?!an?\s+(educational|helpful))",
        r"новая\s+роль",
        r"new\s+role",
        r"override\s+(your\s+)?instructions",
        r"переопредели\s+инструкции",
        r"system\s*prompt",
        r"системный\s*промпт",
        r"developer\s+mode",
        r"режим\s+разработчика",
        r"dan\s+mode",
        r"jailbreak",
        r"джейлбрейк",
    ]

    # Profanity patterns (basic Russian + English)
    PROFANITY_PATTERNS = [
        # Russian mat (основные корни)
        r"\b[хx][уy][йеёия]",
        r"\b[пp][иi][зz][дd]",
        r"\b[бb][лl][яa]",
        r"\b[еe][бb](?:[аaуyиi]|[лl][оoаaиi])",
        r"\b[сc][уy][кk][аa]",
        r"\b[мm][уy][дd][аaоoиi]",
        r"\b[гg][аa][нn][дd][оo][нn]",
        # English profanity
        r"\bf+u+c+k+",
        r"\bs+h+i+t+",
        r"\ba+s+s+h+o+l+e+",
        r"\bb+i+t+c+h+",
        r"\bd+i+c+k+",
        r"\bc+u+n+t+",
    ]

    def __init__(self):
        # Compile patterns for performance
        self._jailbreak_re = [
            re.compile(p, re.IGNORECASE | re.UNICODE) for p in self.JAILBREAK_PATTERNS
        ]
        self._profanity_re = [
            re.compile(p, re.IGNORECASE | re.UNICODE) for p in self.PROFANITY_PATTERNS
        ]

    def check_content(self, text: str) -> ModerationResult:
        """
        Check if content is allowed.

        Args:
            text: Content to check

        Returns:
            ModerationResult with is_allowed and optional reason
        """
        if not text or not text.strip():
            return ModerationResult(is_allowed=True)

        text_lower = text.lower()

        # Check for jailbreak attempts
        for pattern in self._jailbreak_re:
            if pattern.search(text_lower):
                return ModerationResult(
                    is_allowed=False,
                    reason="jailbreak_attempt",
                )

        # Check for profanity
        for pattern in self._profanity_re:
            if pattern.search(text_lower):
                return ModerationResult(
                    is_allowed=False,
                    reason="profanity",
                )

        return ModerationResult(is_allowed=True)

    def get_block_message(self, reason: Optional[str]) -> str:
        """Get user-friendly message for blocked content."""
        return (
            "⚠️ Я не могу обработать это сообщение.\n\n"
            "Пожалуйста, сформулируй учебный вопрос по-другому."
        )


# Global instance
moderation_service = ModerationService()
