"""Configuration loader using environment variables and python-dotenv."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables.

    The API key is excluded from standard representation to ensure it is
    never accidentally logged.
    """

    GEMINI_API_KEY: str = field(default="", repr=False)
    GEMINI_MODEL: str = ""
    MAX_ATTEMPTS: int = 3
    TEST_TIMEOUT_SECONDS: int = 10
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3

    def __repr__(self) -> str:
        """Return a safe string representation with the API key masked."""
        masked_key = "***" if self.GEMINI_API_KEY else ""
        return (
            f"Config(GEMINI_API_KEY={masked_key!r}, "
            f"GEMINI_MODEL={self.GEMINI_MODEL!r}, "
            f"MAX_ATTEMPTS={self.MAX_ATTEMPTS}, "
            f"TEST_TIMEOUT_SECONDS={self.TEST_TIMEOUT_SECONDS}, "
            f"LLM_TIMEOUT_SECONDS={self.LLM_TIMEOUT_SECONDS}, "
            f"LLM_MAX_RETRIES={self.LLM_MAX_RETRIES})"
        )

    def __str__(self) -> str:
        """Return a safe string representation with the API key masked."""
        return self.__repr__()


def load_config(
    dotenv_path: str | Path | None = None,
    override: bool = False,
) -> Config:
    """Load configuration from a .env file (if present) and environment variables."""
    if dotenv_path is not None:
        load_dotenv(dotenv_path=dotenv_path, override=override)
    else:
        load_dotenv(override=override)

    return Config(
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", ""),
        GEMINI_MODEL=os.getenv("GEMINI_MODEL", ""),
        MAX_ATTEMPTS=int(os.getenv("MAX_ATTEMPTS", "3")),
        TEST_TIMEOUT_SECONDS=int(os.getenv("TEST_TIMEOUT_SECONDS", "10")),
        LLM_TIMEOUT_SECONDS=int(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        LLM_MAX_RETRIES=int(os.getenv("LLM_MAX_RETRIES", "3")),
    )


# Load default module-level settings on import
_default_config = load_config()
GEMINI_API_KEY: str = _default_config.GEMINI_API_KEY
GEMINI_MODEL: str = _default_config.GEMINI_MODEL
MAX_ATTEMPTS: int = _default_config.MAX_ATTEMPTS
TEST_TIMEOUT_SECONDS: int = _default_config.TEST_TIMEOUT_SECONDS
LLM_TIMEOUT_SECONDS: int = _default_config.LLM_TIMEOUT_SECONDS
LLM_MAX_RETRIES: int = _default_config.LLM_MAX_RETRIES
