"""Tests for the Streamlit UI in app/main.py using AppTest."""

from __future__ import annotations

from pathlib import Path

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


def test_app_starts_and_sidebar_lists_ten_agents() -> None:
    """Verify the Streamlit app loads without error and lists all 10 agents in the sidebar."""
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


def test_app_test_executor_tab_runs_sample_code() -> None:
    """Verify clicking 'Run tests' runs TestExecutor on the pre-filled buggy sample."""
    at = AppTest.from_file(APP_MAIN_PATH, default_timeout=30)
    at.run()
    assert not at.exception

    # Click the "Run tests" button on the Try the Test Executor tab
    run_button = at.button(key="run_tests_button")
    run_button.click()
    at.run(timeout=30)

    assert not at.exception

    # The pre-filled sample has an intentional bug in add(), so an error banner is shown
    assert len(at.error) >= 1
    assert "passed = False" in at.error[0].value

    metric_labels = {m.label: m.value for m in at.metric}
    assert metric_labels.get("Tests Run") == "2"
    assert metric_labels.get("Passed") == "1"
    assert metric_labels.get("Failed") == "1"
    assert metric_labels.get("Errors") == "0"
