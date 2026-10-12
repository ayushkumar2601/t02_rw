"""Asynchronous LLM client for Groq API with bounded retries, rate-limit backoff,
and strict secret isolation.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

from app.config import settings

logger = logging.getLogger("voice_agent.llm_client")


class LLMError(Exception):
    """Base exception for LLM provider errors."""


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""


class LLMRateLimitError(LLMError):
    """Raised when LLM provider returns HTTP 429 Rate Limit."""


class LLMAuthError(LLMError):
    """Raised on authentication failures (never exposes key)."""


class LLMMalformedResponseError(LLMError):
    """Raised when LLM returns invalid or unparseable JSON."""


class LLMClient:
    """Async client interacting with Groq (or compatible OpenAI endpoints)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.base_url = (base_url or settings.GROQ_API_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries if max_retries is not None else settings.LLM_MAX_RETRIES

    @property
    def is_configured(self) -> bool:
        """Check if an API key is provided and non-empty."""
        return bool(self.api_key and self.api_key.strip())

    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """Call Groq chat completion API with bounded retries and exponential backoff.

        Returns raw assistant response string (sanitized).
        Never exposes the API key in exceptions or logs.
        """
        if not self.is_configured:
            raise LLMAuthError("Groq API key not configured. Offline fallback mode active.")

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        endpoint = f"{self.base_url}/chat/completions"
        delay = 1.0

        for attempt in range(1, self.max_retries + 2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return self._clean_json_markdown(content)

                if response.status_code == 429:
                    logger.warning("Groq rate limit encountered (attempt %d/%d)", attempt, self.max_retries + 1)
                    retry_after_str = response.headers.get("retry-after")
                    retry_after = float(retry_after_str) if retry_after_str else delay
                    if attempt > self.max_retries:
                        raise LLMRateLimitError("Provider rate limit reached (HTTP 429).")
                    await asyncio.sleep(min(retry_after, 5.0))
                    delay *= 2
                    continue

                if response.status_code in (401, 403):
                    raise LLMAuthError("Authentication with LLM provider failed.")

                # Other HTTP errors (5xx, 400, etc.)
                if attempt > self.max_retries:
                    raise LLMError(f"LLM provider error (HTTP {response.status_code}).")

                await asyncio.sleep(delay)
                delay *= 2

            except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
                logger.warning("LLM request timeout (attempt %d/%d)", attempt, self.max_retries + 1)
                if attempt > self.max_retries:
                    raise LLTimeoutError("LLM provider request timed out.") from exc
                await asyncio.sleep(delay)
                delay *= 2

            except httpx.RequestError as exc:
                logger.warning("LLM network request error (attempt %d/%d)", attempt, self.max_retries + 1)
                if attempt > self.max_retries:
                    raise LLMError("LLM network request error.") from exc
                await asyncio.sleep(delay)
                delay *= 2

        raise LLMError("LLM retries exhausted.")

    @staticmethod
    def _clean_json_markdown(raw_content: str) -> str:
        """Strip markdown code block fences and isolate valid JSON."""
        content = raw_content.strip()
        # Remove ```json ... ``` fences if present
        fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
        match = re.match(fence_pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return content


llm_client = LLMClient()
