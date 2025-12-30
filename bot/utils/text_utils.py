"""Text utilities for message processing."""

import re
from typing import List, Optional, Tuple


def split_message(text: str, max_length: int = 4096) -> List[str]:
    """
    Split long message into chunks for Telegram.

    Tries to split at paragraph boundaries, then sentences, then words.

    Args:
        text: Text to split
        max_length: Maximum length of each chunk (Telegram limit is 4096)

    Returns:
        List of text chunks
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Try to split by paragraphs first
    paragraphs = text.split("\n\n")

    for para in paragraphs:
        # If single paragraph is too long, split it further
        if len(para) > max_length:
            # Split by sentences
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                if len(sentence) > max_length:
                    # Split by words as last resort
                    words = sentence.split()
                    for word in words:
                        if len(current_chunk) + len(word) + 1 > max_length:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = word
                        else:
                            current_chunk += " " + word if current_chunk else word
                elif len(current_chunk) + len(sentence) + 1 > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
        elif len(current_chunk) + len(para) + 2 > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def extract_subject(text: str) -> Optional[str]:
    """
    Extract subject tag from AI response.

    Looks for pattern: [SUBJECT: subject_name]

    Args:
        text: AI response text

    Returns:
        Subject name or None if not found
    """
    match = re.search(r"\[SUBJECT:\s*([^\]]+)\]", text)
    if match:
        return match.group(1).strip()
    return None


def remove_subject_tag(text: str) -> str:
    """Remove subject tag from text."""
    return re.sub(r"\n?\[SUBJECT:[^\]]+\]", "", text).strip()


def extract_interview_options(text: str) -> Tuple[str, Optional[List[str]]]:
    """
    Extract interview options from AI response.

    Looks for pattern: [ВАРИАНТЫ: opt1 | opt2 | opt3]

    Args:
        text: AI response text

    Returns:
        tuple(clean_text, options_list or None)
    """
    match = re.search(r"\[ВАРИАНТЫ:\s*([^\]]+)\]", text)
    if match:
        options_str = match.group(1)
        options = [opt.strip() for opt in options_str.split("|")]
        clean_text = re.sub(r"\n?\[ВАРИАНТЫ:[^\]]+\]", "", text).strip()
        return clean_text, options
    return text, None


def should_skip_interview(text: str) -> bool:
    """Check if AI indicated to skip interview."""
    return "[SKIP_INTERVIEW]" in text


def format_tokens(tokens: int) -> str:
    """Format token count for display."""
    if tokens >= 1000000:
        return f"{tokens / 1000000:.1f}M"
    if tokens >= 1000:
        return f"{tokens / 1000:.1f}K"
    return str(tokens)


def escape_markdown(text: str) -> str:
    """Escape special Markdown characters for safe sending."""
    # Characters that need escaping in Telegram Markdown
    special_chars = ['_', '*', '`', '[']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text


def sanitize_markdown(text: str) -> str:
    """
    Try to fix common Markdown issues.

    - Ensures code blocks are closed
    - Ensures inline code is closed
    - Ensures bold/italic markers are balanced
    """
    # Fix unclosed code blocks (```)
    code_block_count = text.count('```')
    if code_block_count % 2 != 0:
        text += '\n```'

    # Fix unclosed inline code (`)
    # Count backticks not part of code blocks
    temp = text.replace('```', '')
    backtick_count = temp.count('`')
    if backtick_count % 2 != 0:
        text += '`'

    # Fix unclosed bold (**)
    bold_count = text.count('**')
    if bold_count % 2 != 0:
        text += '**'

    # Fix unclosed italic (single *)
    # This is tricky because * is also used in bold
    # Simple approach: count standalone * not part of **
    temp = text.replace('**', '')
    star_count = temp.count('*')
    if star_count % 2 != 0:
        text += '*'

    return text
