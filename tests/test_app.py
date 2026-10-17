"""Tests for the Streamlit UI in app/main.py using AppTest."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_MAIN_PATH = Path(__file__).resolve().parent.parent / "app" / "main.py"

EXPECTED_SIDEBAR_AGENTS = [
    "Orchestrator",
    "Analyzer",
    "Test Generator",
    "Test Executor",
    "Localizer",
    "Debugger",
    "Repairer",
    "Reviewer",
    "Validator",
    "Reporter",
]


def test_app_starts_and_sidebar_lists_ten_agents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the Streamlit app loads without error and lists all 10 agents in the sidebar."""
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    at = AppTest.from_file(APP_MAIN_PATH, default_timeout=30)
    at.run()

    assert not at.exception
    assert len(at.title) == 1
    assert (
        at.title[0].value
        == "Multi-Agent AI System for Autonomous Software Testing, Debugging and Program Repair"
    )

    sidebar_markdown = "\n".join(md.value for md in at.sidebar.markdown)
    for agent_name in EXPECTED_SIDEBAR_AGENTS:
        assert agent_name in sidebar_markdown

    assert "Implemented" in sidebar_markdown
    assert "Not implemented yet" in sidebar_markdown
    assert "1 / 10 implemented" in sidebar_markdown


def test_app_test_executor_tab_runs_sample_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify clicking 'Run tests' runs TestExecutor on the pre-filled buggy sample."""
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.setenv("ENABLE_CODE_EXECUTION", "true")

    at = AppTest.from_file(APP_MAIN_PATH, default_timeout=30)
    at.run()
    assert not at.exception

    # Editable text areas are present when ENABLE_CODE_EXECUTION=true
    assert len(at.text_area) == 2

    run_button = at.button(key="run_tests_button")
    run_button.click()
    at.run(timeout=30)

    assert not at.exception
    assert len(at.error) >= 1
    assert "passed = False" in at.error[0].value

    metric_labels = {m.label: m.value for m in at.metric}
    assert metric_labels.get("Tests Run") == "2"
    assert metric_labels.get("Passed") == "1"
    assert metric_labels.get("Failed") == "1"
    assert metric_labels.get("Errors") == "0"


def test_app_disabled_code_execution_mode_uses_builtin_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ENABLE_CODE_EXECUTION is false, free-form text areas are hidden and 3 built-in samples are offered."""
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.setenv("ENABLE_CODE_EXECUTION", "false")

    at = AppTest.from_file(APP_MAIN_PATH, default_timeout=30)
    at.run()
    assert not at.exception

    # No editable text areas for user code in disabled mode
    assert len(at.text_area) == 0

    # Info banner explains why free-form code execution is disabled
    info_messages = "\n".join(info.value for info in at.info)
    assert "disabled on the hosted version" in info_messages

    # Selectbox provides the 3 built-in sample programs
    selector = at.selectbox(key="sample_program_selector")
    assert len(selector.options) == 3

    # Select the "Correct program (all tests pass)" sample and click Run tests
    selector.select("Correct program (all tests pass)").run(timeout=30)
    at.button(key="run_tests_button").click().run(timeout=30)

    assert not at.exception
    assert len(at.success) >= 1
    assert "passed = True" in at.success[0].value


def test_app_password_gate_blocks_and_unlocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify APP_PASSWORD blocks content until the valid password is provided."""
    monkeypatch.setenv("APP_PASSWORD", "correct-horse-battery-staple")
    monkeypatch.setenv("ENABLE_CODE_EXECUTION", "false")

    at = AppTest.from_file(APP_MAIN_PATH, default_timeout=30)
    at.run()
    assert not at.exception

    # Main title and sidebar are hidden behind the password prompt
    assert len(at.title) == 0
    assert len(at.sidebar.markdown) == 0

    # Entering an invalid password shows an error and keeps content hidden
    pwd_input = at.text_input(key="app_password_input")
    pwd_input.set_value("wrong-password").run()
    assert not at.exception
    assert len(at.title) == 0
    assert any("Incorrect password" in err.value for err in at.error)

    # Entering the valid password unlocks the app and stores state in session_state
    at.text_input(key="app_password_input").set_value(
        "correct-horse-battery-staple"
    ).run()
    assert not at.exception
    assert at.session_state["authenticated"] is True
    assert len(at.title) == 1
    assert len(at.sidebar.markdown) > 0
