"""Model-agnostic LLM client interface, Gemini implementation, and test fake."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from google import genai
from google.genai import types

from core.config import load_config


class LLMClient(ABC):
    """Abstract interface for Large Language Model clients."""

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate a text completion for a given prompt and optional system prompt."""
        raise NotImplementedError


class GeminiClient(LLMClient):
    """Google Gemini LLM client using the official google-genai SDK.

    Supports request timeouts and exponential backoff retries on API failures.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int | float | None = None,
        max_retries: int | None = None,
        base_delay: float = 1.0,
        client: Any | None = None,
    ) -> None:
        """Initialize the Gemini client from arguments or environment config."""
        cfg = load_config()
        self._api_key: str = api_key if api_key is not None else cfg.GEMINI_API_KEY
        self.model: str = model if model is not None else cfg.GEMINI_MODEL
        self.timeout_seconds: float = (
            float(timeout_seconds)
            if timeout_seconds is not None
            else float(cfg.LLM_TIMEOUT_SECONDS)
        )
        self.max_retries: int = (
            int(max_retries) if max_retries is not None else int(cfg.LLM_MAX_RETRIES)
        )
        self.base_delay: float = float(base_delay)

        if not self.model:
            raise ValueError("GEMINI_MODEL must be specified in config or arguments.")

        if client is not None:
            self._client = client
        else:
            if not self._api_key:
                raise ValueError(
                    "GEMINI_API_KEY must be specified in config or arguments."
                )
            self._client = genai.Client(api_key=self._api_key)

    def __repr__(self) -> str:
        """Return a safe representation that never exposes the API key."""
        return (
            f"GeminiClient(model={self.model!r}, "
            f"timeout_seconds={self.timeout_seconds}, "
            f"max_retries={self.max_retries})"
        )

    def generate(self, prompt: str, system: str | None = None) -> str:
        """Call Gemini generate_content with timeout and exponential backoff retry."""
        timeout_ms = int(self.timeout_seconds * 1000)
        config = types.GenerateContentConfig(
            system_instruction=system,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )

        attempts = max(1, self.max_retries)
        last_exception: Exception | None = None

        for attempt in range(attempts):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                return response.text or ""
            except Exception as exc:
                last_exception = exc
                if attempt < attempts - 1:
                    delay = self.base_delay * (2**attempt)
                    time.sleep(delay)

        assert last_exception is not None
        raise last_exception


class FakeLLMClient(LLMClient):
    """Deterministic fake LLM client that returns scripted responses for testing."""

    def __init__(self, responses: Sequence[str] | str | None = None) -> None:
        """Initialize with a sequence of scripted responses or a single response."""
        if isinstance(responses, str):
            self.responses: list[str] = [responses]
        elif responses is None:
            self.responses = []
        else:
            self.responses = list(responses)

        self.calls: list[dict[str, str | None]] = []
        self._index: int = 0

    def generate(self, prompt: str, system: str | None = None) -> str:
        """Record the call and return the next scripted response."""
        self.calls.append({"prompt": prompt, "system": system})
        if self._index >= len(self.responses):
            raise IndexError("No more scripted responses available in FakeLLMClient.")
        response = self.responses[self._index]
        self._index += 1
        return response
