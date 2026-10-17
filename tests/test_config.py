"""Tests for core.config environment loading and safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config import Config, load_config


def test_load_config_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify default values when optional variables are not set."""
    for key in (
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "MAX_ATTEMPTS",
        "TEST_TIMEOUT_SECONDS",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_RETRIES",
    ):
        monkeypatch.delenv(key, raising=False)

    empty_env = tmp_path / ".env.empty"
    empty_env.write_text("", encoding="utf-8")

    cfg = load_config(dotenv_path=empty_env, override=True)
    assert isinstance(cfg, Config)
    assert cfg.GEMINI_API_KEY == ""
    assert cfg.GEMINI_MODEL == ""
    assert cfg.MAX_ATTEMPTS == 3
    assert cfg.TEST_TIMEOUT_SECONDS == 10
    assert cfg.LLM_TIMEOUT_SECONDS == 60
    assert cfg.LLM_MAX_RETRIES == 3


def test_load_config_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify settings are loaded accurately from a .env file."""
    for key in (
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "MAX_ATTEMPTS",
        "TEST_TIMEOUT_SECONDS",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_RETRIES",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "GEMINI_API_KEY=test_dummy_key_value\n"
        "GEMINI_MODEL=test-model-name\n"
        "MAX_ATTEMPTS=5\n"
        "TEST_TIMEOUT_SECONDS=25\n"
        "LLM_TIMEOUT_SECONDS=90\n"
        "LLM_MAX_RETRIES=4\n",
        encoding="utf-8",
    )

    cfg = load_config(dotenv_path=env_file, override=True)
    assert cfg.GEMINI_API_KEY == "test_dummy_key_value"
    assert cfg.GEMINI_MODEL == "test-model-name"
    assert cfg.MAX_ATTEMPTS == 5
    assert cfg.TEST_TIMEOUT_SECONDS == 25
    assert cfg.LLM_TIMEOUT_SECONDS == 90
    assert cfg.LLM_MAX_RETRIES == 4


def test_config_repr_masks_api_key() -> None:
    """Ensure the API key is never exposed in string or repr output."""
    cfg = Config(GEMINI_API_KEY="super_sensitive_token", GEMINI_MODEL="test-model")
    assert "super_sensitive_token" not in repr(cfg)
    assert "super_sensitive_token" not in str(cfg)
    assert "***" in repr(cfg)
