"""OpenRouter API client for LLM interactions."""

import asyncio
import base64
import logging
import time
from typing import Any, Dict, List, Optional, Union

import aiohttp
from aiohttp import ClientTimeout

from bot.config import settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Async client for OpenRouter API with retry logic."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
    ):
        self.api_key = api_key or settings.openrouter_api_key
        self.model = model or settings.openrouter_model
        self.max_tokens = max_tokens or settings.openrouter_max_tokens
        self.temperature = temperature or settings.openrouter_temperature
        self.timeout = ClientTimeout(total=timeout or settings.openrouter_timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://eduhelper.bot",
                    "X-Title": "EduHelper Bot",
                },
            )
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        session = await self._get_session()
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(max_attempts):
            try:
                async with session.request(method, url, json=json_data) as resp:
                    if resp.status == 429:  # Rate limit
                        retry_after = int(resp.headers.get("Retry-After", 5))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    if resp.status >= 500:  # Server error
                        logger.warning(f"Server error {resp.status}, retrying...")
                        await asyncio.sleep(1 * (attempt + 1))
                        continue

                    resp.raise_for_status()
                    return await resp.json()

            except aiohttp.ClientConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
                if attempt + 1 == max_attempts:
                    raise
                await asyncio.sleep(0.5 * (attempt + 1))

            except asyncio.TimeoutError:
                logger.warning(f"Timeout (attempt {attempt + 1})")
                if attempt + 1 == max_attempts:
                    raise
                await asyncio.sleep(1)

        raise RuntimeError("Max retry attempts exceeded")

    def _build_message_content(
        self,
        text: str,
        image_base64: Optional[str] = None,
        voice_base64: Optional[str] = None,
    ) -> Union[str, List[dict]]:
        """Build message content with optional image and voice."""
        if not image_base64 and not voice_base64:
            return text

        content = [{"type": "text", "text": text}]

        if image_base64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
            })

        if voice_base64:
            content.append({
                "type": "input_audio",
                "input_audio": {
                    "data": voice_base64,
                    "format": "ogg",
                },
            })

        return content

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        image_base64: Optional[str] = None,
        voice_base64: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            image_base64: Optional base64-encoded image
            voice_base64: Optional base64-encoded voice (OGG format)
            system_prompt: Optional system prompt to prepend

        Returns:
            dict with 'content', 'tokens', 'response_time_ms'
        """
        start_time = time.time()

        # Build messages list
        request_messages = []

        if system_prompt:
            request_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            if msg["role"] == "user" and (image_base64 or voice_base64) and msg == messages[-1]:
                # Add image/voice to the last user message
                request_messages.append(
                    {
                        "role": "user",
                        "content": self._build_message_content(
                            msg["content"], image_base64, voice_base64
                        ),
                    }
                )
            else:
                request_messages.append(msg)

        payload = {
            "model": self.model,
            "messages": request_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        # Debug: log if audio is being sent
        has_audio = any(
            isinstance(msg.get("content"), list) and
            any(c.get("type") == "input_audio" for c in msg["content"])
            for msg in request_messages
        )
        if has_audio:
            logger.info(f"Sending request with audio to model: {self.model}")

        response = await self._request_with_retry("POST", "/chat/completions", payload)

        response_time_ms = int((time.time() - start_time) * 1000)

        # Parse response
        content = response["choices"][0]["message"]["content"]
        usage = response.get("usage", {})

        return {
            "content": content,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "response_time_ms": response_time_ms,
            "model": self.model,
        }

    async def ask_question(
        self,
        question: str,
        system_prompt: str,
        image_base64: Optional[str] = None,
        voice_base64: Optional[str] = None,
        context: Optional[List[dict]] = None,
    ) -> Dict[str, Any]:
        """
        Simple interface for asking a single question.

        Args:
            question: User's question
            system_prompt: System prompt for AI behavior
            image_base64: Optional base64-encoded image
            voice_base64: Optional base64-encoded voice (OGG format)
            context: Optional previous messages for context

        Returns:
            dict with response data
        """
        messages = context or []
        messages.append({"role": "user", "content": question})

        return await self.chat_completion(
            messages=messages,
            image_base64=image_base64,
            voice_base64=voice_base64,
            system_prompt=system_prompt,
        )


    # Faster-Whisper for local speech-to-text transcription
    _whisper_model = None

    @classmethod
    def _get_whisper_model(cls):
        """Lazy load Whisper model."""
        if cls._whisper_model is None:
            from faster_whisper import WhisperModel
            logger.info("Loading Whisper model (small)...")
            # Use "small" for balance of speed/quality on CPU
            # Options: tiny, base, small, medium, large-v3, turbo
            cls._whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("Whisper model loaded")
        return cls._whisper_model

    async def transcribe_voice(self, voice_base64: str) -> Optional[Dict[str, Any]]:
        """
        Transcribe voice message using local Faster-Whisper.

        Args:
            voice_base64: Base64-encoded OGG audio

        Returns:
            Dict with 'text', 'prompt_tokens', 'completion_tokens', 'cost_usd' or None if failed
        """
        import tempfile
        import os

        start_time = time.time()

        try:
            # Decode base64 to bytes
            audio_bytes = base64.b64decode(voice_base64)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            try:
                # Run transcription in thread pool (CPU-bound)
                loop = asyncio.get_event_loop()
                transcription = await loop.run_in_executor(
                    None,
                    self._transcribe_sync,
                    temp_path,
                )

                response_time_ms = int((time.time() - start_time) * 1000)
                logger.info(f"Voice transcribed in {response_time_ms}ms: {transcription[:100]}...")

                return {
                    "text": transcription,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,  # Local - free!
                    "response_time_ms": response_time_ms,
                }

            finally:
                # Cleanup temp file
                os.unlink(temp_path)

        except Exception as e:
            logger.error(f"Voice transcription failed: {e}")
            return None

    def _transcribe_sync(self, audio_path: str) -> str:
        """Synchronous transcription (runs in thread pool)."""
        model = self._get_whisper_model()
        segments, info = model.transcribe(
            audio_path,
            language="ru",
            vad_filter=True,  # Remove silence
            beam_size=5,
        )
        return " ".join([segment.text.strip() for segment in segments])


# Global client instance
openrouter_client = OpenRouterClient()
