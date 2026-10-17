"""Tests for RunLogger JSONL write/read round trip in core.logger."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.logger import RunLogger


def test_run_logger_write_and_read_round_trip(tmp_path: Path) -> None:
    """Verify writing multiple interactions to log.jsonl and reading them back."""
    logger = RunLogger(run_id="test_run_123", base_dir=tmp_path)
    expected_path = tmp_path / "test_run_123" / "log.jsonl"

    assert logger.read_log() == []

    logger.log_interaction(
        agent_name="Analyzer",
        input_summary="source_code length=42",
        prompt=None,
        raw_output="functions=['divide']",
        duration=0.015,
        timestamp="2026-10-17T12:00:00+00:00",
    )
    logger.log_interaction(
        agent_name="TestGenerator",
        input_summary="generate tests for divide",
        prompt="Write pytest tests for divide(a, b)",
        raw_output="def test_divide(): assert divide(4, 2) == 2",
        duration=1.234,
        timestamp="2026-10-17T12:00:02+00:00",
    )

    assert expected_path.exists()

    logs = logger.read_log()
    assert len(logs) == 2

    assert logs[0] == {
        "agent_name": "Analyzer",
        "timestamp": "2026-10-17T12:00:00+00:00",
        "input_summary": "source_code length=42",
        "prompt": None,
        "raw_output": "functions=['divide']",
        "duration": 0.015,
    }
    assert logs[1] == {
        "agent_name": "TestGenerator",
        "timestamp": "2026-10-17T12:00:02+00:00",
        "input_summary": "generate tests for divide",
        "prompt": "Write pytest tests for divide(a, b)",
        "raw_output": "def test_divide(): assert divide(4, 2) == 2",
        "duration": 1.234,
    }


def test_run_logger_rejects_empty_run_id(tmp_path: Path) -> None:
    """Verify RunLogger raises ValueError on an empty run_id."""
    with pytest.raises(ValueError, match="run_id"):
        RunLogger(run_id="   ", base_dir=tmp_path)
