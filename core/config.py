"""Configuration loader supporting environment variables, .env, and st.secrets."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _parse_bool(value: Any, default: bool = False) -> bool:
    """Parse a boolean from a bool, int, or string value."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    return default


def _get_streamlit_secrets() -> Mapping[str, Any]:
    """Return st.secrets as a mapping if available, or an empty dict otherwise."""
    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            # Trigger access inside try block in case secrets.toml is absent
            _ = len(st.secrets)
            return st.secrets
    except Exception:
        return {}
    return {}


def _resolve_value(
    key: str,
    secrets: Mapping[str, Any],
) -> Any | None:
    """Read a setting from os.environ first, then from st.secrets."""
    env_val = os.environ.get(key)
    if env_val is not None and env_val != "":
        return env_val

    try:
        if secrets and key in secrets:
            sec_val = secrets[key]
            if sec_val is not None and str(sec_val) != "":
                return sec_val
    except Exception:
        pass

    return None


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables or st.secrets.

    Sensitive fields (GEMINI_API_KEY, APP_PASSWORD) are excluded from standard
    representation so they are never accidentally logged or displayed.
    """

    GEMINI_API_KEY: str = field(default="", repr=False)
    GEMINI_MODEL: str = ""
    MAX_ATTEMPTS: int = 3
    TEST_TIMEOUT_SECONDS: int = 10
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3
    ENABLE_CODE_EXECUTION: bool = False
    APP_PASSWORD: str = field(default="", repr=False)

    def __repr__(self) -> str:
        """Return a safe string representation with secrets masked."""
        masked_key = "***" if self.GEMINI_API_KEY else ""
        masked_pwd = "***" if self.APP_PASSWORD else ""
        return (
            f"Config(GEMINI_API_KEY={masked_key!r}, "
            f"GEMINI_MODEL={self.GEMINI_MODEL!r}, "
            f"MAX_ATTEMPTS={self.MAX_ATTEMPTS}, "
            f"TEST_TIMEOUT_SECONDS={self.TEST_TIMEOUT_SECONDS}, "
            f"LLM_TIMEOUT_SECONDS={self.LLM_TIMEOUT_SECONDS}, "
            f"LLM_MAX_RETRIES={self.LLM_MAX_RETRIES}, "
            f"ENABLE_CODE_EXECUTION={self.ENABLE_CODE_EXECUTION}, "
            f"APP_PASSWORD={masked_pwd!r})"
        )

    def __str__(self) -> str:
        """Return a safe string representation with secrets masked."""
        return self.__repr__()


def load_config(
    dotenv_path: str | Path | None = None,
    override: bool = False,
    secrets: Mapping[str, Any] | None = None,
) -> Config:
    """Load configuration with precedence: os.environ -> st.secrets -> defaults.

    ENABLE_CODE_EXECUTION defaults to True locally when a `.env` file exists,
    and False when running hosted without a `.env` file.
    """
    if dotenv_path is not None:
        dotenv_file = Path(dotenv_path)
        load_dotenv(dotenv_path=dotenv_file, override=override)
        has_local_dotenv = dotenv_file.name == ".env" and dotenv_file.is_file()
    else:
        default_dotenv = PROJECT_ROOT / ".env"
        load_dotenv(dotenv_path=default_dotenv, override=override)
        has_local_dotenv = default_dotenv.is_file()

    active_secrets = secrets if secrets is not None else _get_streamlit_secrets()

    api_key = str(_resolve_value("GEMINI_API_KEY", active_secrets) or "")
    model = str(_resolve_value("GEMINI_MODEL", active_secrets) or "")
    max_attempts = int(_resolve_value("MAX_ATTEMPTS", active_secrets) or 3)
    test_timeout = int(_resolve_value("TEST_TIMEOUT_SECONDS", active_secrets) or 10)
    llm_timeout = int(_resolve_value("LLM_TIMEOUT_SECONDS", active_secrets) or 60)
    llm_retries = int(_resolve_value("LLM_MAX_RETRIES", active_secrets) or 3)

    raw_exec_flag = _resolve_value("ENABLE_CODE_EXECUTION", active_secrets)
    enable_code_exec = _parse_bool(raw_exec_flag, default=has_local_dotenv)

    app_password = str(_resolve_value("APP_PASSWORD", active_secrets) or "")

    return Config(
        GEMINI_API_KEY=api_key,
        GEMINI_MODEL=model,
        MAX_ATTEMPTS=max_attempts,
        TEST_TIMEOUT_SECONDS=test_timeout,
        LLM_TIMEOUT_SECONDS=llm_timeout,
        LLM_MAX_RETRIES=llm_retries,
        ENABLE_CODE_EXECUTION=enable_code_exec,
        APP_PASSWORD=app_password,
    )


# Load default module-level settings on import
_default_config = load_config()
GEMINI_API_KEY: str = _default_config.GEMINI_API_KEY
GEMINI_MODEL: str = _default_config.GEMINI_MODEL
MAX_ATTEMPTS: int = _default_config.MAX_ATTEMPTS
TEST_TIMEOUT_SECONDS: int = _default_config.TEST_TIMEOUT_SECONDS
LLM_TIMEOUT_SECONDS: int = _default_config.LLM_TIMEOUT_SECONDS
LLM_MAX_RETRIES: int = _default_config.LLM_MAX_RETRIES
ENABLE_CODE_EXECUTION: bool = _default_config.ENABLE_CODE_EXECUTION
APP_PASSWORD: str = _default_config.APP_PASSWORD
