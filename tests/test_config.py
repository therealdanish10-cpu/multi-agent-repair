"""Tests for core.config environment loading, st.secrets fallback, and safety."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.config import Config, load_config

ALL_CONFIG_KEYS = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "MAX_ATTEMPTS",
    "TEST_TIMEOUT_SECONDS",
    "LLM_TIMEOUT_SECONDS",
    "LLM_MAX_RETRIES",
    "ENABLE_CODE_EXECUTION",
    "APP_PASSWORD",
)


def _clear_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all configuration keys from os.environ for isolated testing."""
    for key in ALL_CONFIG_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_load_config_defaults_when_no_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify default values when neither .env nor st.secrets is present."""
    _clear_config_env(monkeypatch)
    empty_env = tmp_path / ".env.empty"
    empty_env.write_text("", encoding="utf-8")

    cfg = load_config(dotenv_path=empty_env, override=True, secrets={})
    assert isinstance(cfg, Config)
    assert cfg.GEMINI_API_KEY == ""
    assert cfg.GEMINI_MODEL == ""
    assert cfg.MAX_ATTEMPTS == 3
    assert cfg.TEST_TIMEOUT_SECONDS == 10
    assert cfg.LLM_TIMEOUT_SECONDS == 60
    assert cfg.LLM_MAX_RETRIES == 3
    assert cfg.ENABLE_CODE_EXECUTION is False
    assert cfg.APP_PASSWORD == ""


def test_load_config_from_local_dotenv_enables_code_execution_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify settings load from a local .env file and ENABLE_CODE_EXECUTION defaults to True."""
    _clear_config_env(monkeypatch)
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

    cfg = load_config(dotenv_path=env_file, override=True, secrets={})
    assert cfg.GEMINI_API_KEY == "test_dummy_key_value"
    assert cfg.GEMINI_MODEL == "test-model-name"
    assert cfg.MAX_ATTEMPTS == 5
    assert cfg.TEST_TIMEOUT_SECONDS == 25
    assert cfg.LLM_TIMEOUT_SECONDS == 90
    assert cfg.LLM_MAX_RETRIES == 4
    assert cfg.ENABLE_CODE_EXECUTION is True


def test_config_fallback_order_env_beats_st_secrets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify os.environ takes priority over st.secrets, and st.secrets beats defaults."""
    _clear_config_env(monkeypatch)
    empty_env = tmp_path / ".env.empty"
    empty_env.write_text("", encoding="utf-8")

    # Set GEMINI_MODEL and MAX_ATTEMPTS in environment variables
    monkeypatch.setenv("GEMINI_MODEL", "model-from-env")
    monkeypatch.setenv("MAX_ATTEMPTS", "2")

    # Provide both overlapping and non-overlapping values in secrets
    fake_secrets = {
        "GEMINI_API_KEY": "key-from-st-secrets",
        "GEMINI_MODEL": "model-from-st-secrets",
        "MAX_ATTEMPTS": 5,
        "TEST_TIMEOUT_SECONDS": 18,
        "ENABLE_CODE_EXECUTION": False,
        "APP_PASSWORD": "secret-gate-password",
    }

    cfg = load_config(dotenv_path=empty_env, override=False, secrets=fake_secrets)

    # Environment variable wins over st.secrets
    assert cfg.GEMINI_MODEL == "model-from-env"
    assert cfg.MAX_ATTEMPTS == 2

    # st.secrets is used when environment variable is not set
    assert cfg.GEMINI_API_KEY == "key-from-st-secrets"
    assert cfg.TEST_TIMEOUT_SECONDS == 18
    assert cfg.ENABLE_CODE_EXECUTION is False
    assert cfg.APP_PASSWORD == "secret-gate-password"


def test_config_repr_masks_api_key_and_password() -> None:
    """Ensure neither GEMINI_API_KEY nor APP_PASSWORD is exposed in string/repr output."""
    cfg = Config(
        GEMINI_API_KEY="super_sensitive_token",
        GEMINI_MODEL="test-model",
        APP_PASSWORD="my_secret_password",
    )
    assert "super_sensitive_token" not in repr(cfg)
    assert "super_sensitive_token" not in str(cfg)
    assert "my_secret_password" not in repr(cfg)
    assert "my_secret_password" not in str(cfg)
    assert "***" in repr(cfg)
