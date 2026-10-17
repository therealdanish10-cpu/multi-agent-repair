"""Tests for FakeLLMClient and GeminiClient retry behaviour in core.llm."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core.llm import FakeLLMClient, GeminiClient


def test_fake_llm_client_scripted_responses() -> None:
    """Verify FakeLLMClient returns scripted responses in order and records calls."""
    fake = FakeLLMClient(responses=["first reply", "second reply"])

    res1 = fake.generate("Prompt 1", system="System A")
    res2 = fake.generate("Prompt 2")

    assert res1 == "first reply"
    assert res2 == "second reply"
    assert fake.calls == [
        {"prompt": "Prompt 1", "system": "System A"},
        {"prompt": "Prompt 2", "system": None},
    ]

    with pytest.raises(IndexError):
        fake.generate("Prompt 3")


def test_gemini_client_retry_succeeds_after_transient_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify GeminiClient retries with exponential backoff and returns on success."""
    sleep_delays: list[float] = []
    monkeypatch.setattr("core.llm.time.sleep", lambda d: sleep_delays.append(d))

    mock_sdk_client = MagicMock()
    mock_sdk_client.models.generate_content.side_effect = [
        RuntimeError("Transient 503 Service Unavailable"),
        RuntimeError("Transient 429 Rate Limit"),
        SimpleNamespace(text="Repaired code output"),
    ]

    client = GeminiClient(
        api_key="dummy_test_key",
        model="test-gemini-model",
        timeout_seconds=15,
        max_retries=3,
        base_delay=0.5,
        client=mock_sdk_client,
    )

    output = client.generate("Fix the bug", system="You are a Python repair agent")
    assert output == "Repaired code output"
    assert mock_sdk_client.models.generate_content.call_count == 3
    assert sleep_delays == [0.5, 1.0]


def test_gemini_client_raises_after_exhausting_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify GeminiClient raises the last exception when all retries fail."""
    sleep_delays: list[float] = []
    monkeypatch.setattr("core.llm.time.sleep", lambda d: sleep_delays.append(d))

    mock_sdk_client = MagicMock()
    mock_sdk_client.models.generate_content.side_effect = RuntimeError("API Down")

    client = GeminiClient(
        api_key="dummy_test_key",
        model="test-gemini-model",
        timeout_seconds=10,
        max_retries=3,
        base_delay=1.0,
        client=mock_sdk_client,
    )

    with pytest.raises(RuntimeError, match="API Down"):
        client.generate("Test prompt")

    assert mock_sdk_client.models.generate_content.call_count == 3
    assert sleep_delays == [1.0, 2.0]
