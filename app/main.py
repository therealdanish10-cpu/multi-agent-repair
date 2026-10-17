"""Streamlit web interface for the multi-agent-repair system."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path when launched via `streamlit run app/main.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from agents.test_executor import TestExecutor
from app.helpers import (
    DEFAULT_SAMPLE_CODE,
    DEFAULT_SAMPLE_TESTS,
    build_pipeline_dot,
    detect_agent_statuses,
    list_available_runs,
    load_run_logs,
)

PAGE_TITLE = (
    "Multi-Agent AI System for Autonomous Software Testing, "
    "Debugging and Program Repair"
)
PAGE_SUBTITLE = (
    "Supervisor-orchestrated multi-agent pipeline for automated test generation, "
    "isolated pytest execution, fault localization, and iterative bug repair."
)


def _render_sidebar() -> None:
    """Render the sidebar listing all ten agents, their types, and live status."""
    with st.sidebar:
        st.header("System Agents (10)")
        st.caption(
            "Status is detected automatically by invoking each agent on a "
            "throwaway state without making any external LLM calls."
        )
        statuses = detect_agent_statuses()
        implemented_count = sum(1 for item in statuses if item["implemented"])
        st.markdown(f"**Progress:** {implemented_count} / {len(statuses)} implemented")
        st.divider()

        for item in statuses:
            badge_icon = "🟢" if item["implemented"] else "⚪"
            st.markdown(
                f"**{item['display_name']}** (`{item['type_label']}`)  \n"
                f"{badge_icon} *{item['status_badge']}*"
            )


def _render_pipeline_tab() -> None:
    """Render the supervisor workflow Graphviz diagram and agent type legend."""
    st.subheader("Supervisor / Orchestrator Repair Workflow")
    st.markdown(
        "The **Orchestrator** coordinates ten specialized agents with up to "
        "**3 repair attempts** per bug. Repair success or failure is determined "
        "strictly by real `pytest` execution results."
    )

    col_legend_1, col_legend_2, col_legend_3 = st.columns(3)
    with col_legend_1:
        st.markdown("🟦 **Code-based Agent** (`Orchestrator`, `Analyzer`, `Localizer`, `Validator`, `Reporter`)")
    with col_legend_2:
        st.markdown("🟨 **LLM-powered Agent** (`Test Generator`, `Debugger`, `Repairer`, `Reviewer`)")
    with col_legend_3:
        st.markdown("🟩 **Tool-based Agent** (`Test Executor`)")

    st.graphviz_chart(build_pipeline_dot(), use_container_width=True)


def _render_test_results(result: dict[str, Any]) -> None:
    """Render TestExecutor.execute() results including banner, metrics, failures, and logs."""
    if result.get("timed_out"):
        st.warning(
            "Execution timed out! The test process was terminated after exceeding "
            "the configured timeout."
        )

    if result.get("passed"):
        st.success("All tests passed! (passed = True)")
    else:
        st.error("Tests failed or encountered errors. (passed = False)")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Tests Run", result.get("num_tests", 0))
    m2.metric("Passed", result.get("num_passed", 0))
    m3.metric("Failed", result.get("num_failed", 0))
    m4.metric("Errors", result.get("num_errors", 0))
    m5.metric("Duration", f"{result.get('duration_seconds', 0.0):.2f}s")

    failures: list[dict[str, str]] = result.get("failures", [])
    if failures:
        st.markdown("#### Failures & Errors")
        summary_rows = [
            {
                "Test Name": f.get("test_name", ""),
                "Message": f.get("message", ""),
            }
            for f in failures
        ]
        st.table(summary_rows)

        for idx, failure in enumerate(failures, start=1):
            title = f"{idx}. {failure.get('test_name', 'test')} — {failure.get('message', '')}"
            with st.expander(title, expanded=True):
                st.code(failure.get("traceback", "") or "No traceback available.", language="text")

    with st.expander("Standard Output (stdout)", expanded=False):
        st.code(result.get("stdout", "") or "(empty)", language="text")

    with st.expander("Standard Error (stderr)", expanded=False):
        st.code(result.get("stderr", "") or "(empty)", language="text")


def _render_test_executor_tab() -> None:
    """Render the interactive TestExecutor sandbox tab."""
    st.subheader("Try the Test Executor")
    st.markdown(
        "Enter Python source code (`solution.py`) and a `pytest` suite "
        "(`test_solution.py`). Clicking **Run tests** executes `pytest` in an "
        "isolated temporary directory using `TestExecutor.execute()`."
    )

    col_code, col_tests = st.columns(2)
    with col_code:
        code_input = st.text_area(
            "Python code (saved as solution.py)",
            value=DEFAULT_SAMPLE_CODE,
            height=240,
            key="executor_code_input",
        )
    with col_tests:
        tests_input = st.text_area(
            "pytest tests (saved as test_solution.py)",
            value=DEFAULT_SAMPLE_TESTS,
            height=240,
            key="executor_tests_input",
        )

    if st.button("Run tests", type="primary", key="run_tests_button"):
        executor = TestExecutor()
        with st.spinner("Running pytest in isolated temporary directory..."):
            result = executor.execute(code=code_input, tests=tests_input)
        st.session_state["last_executor_result"] = result

    if "last_executor_result" in st.session_state:
        st.divider()
        _render_test_results(st.session_state["last_executor_result"])


def _render_run_logs_tab() -> None:
    """Render the Run Logs viewer tab reading from runs/<run_id>/log.jsonl."""
    st.subheader("Run Logs")
    runs_dir = PROJECT_ROOT / "runs"
    run_ids = list_available_runs(runs_dir)

    if not run_ids:
        st.info("No runs recorded yet. Logs written to `runs/<run_id>/log.jsonl` will appear here.")
        return

    selected_run = st.selectbox("Select a run ID", options=run_ids, key="run_selector")
    if not selected_run:
        return

    entries = load_run_logs(selected_run, runs_dir=runs_dir)
    if not entries:
        st.info(f"Run `{selected_run}` has no log entries yet.")
        return

    table_rows = [
        {
            "Agent": entry.get("agent_name", ""),
            "Timestamp": entry.get("timestamp", ""),
            "Duration (s)": f"{float(entry.get('duration', 0.0)):.4f}",
        }
        for entry in entries
    ]
    st.table(table_rows)

    st.markdown("#### Interaction Details")
    for idx, entry in enumerate(entries, start=1):
        header = (
            f"Step {idx}: {entry.get('agent_name', 'Agent')} "
            f"({float(entry.get('duration', 0.0)):.4f}s)"
        )
        with st.expander(header, expanded=False):
            st.markdown(f"**Timestamp:** `{entry.get('timestamp', '')}`")
            st.markdown(f"**Input Summary:** `{entry.get('input_summary', '')}`")
            if entry.get("prompt") is not None:
                st.markdown("**Prompt:**")
                st.code(str(entry.get("prompt")), language="text")
            if entry.get("raw_output") is not None:
                st.markdown("**Raw Output:**")
                st.code(str(entry.get("raw_output")), language="text")


def main() -> None:
    """Configure page and render the main Streamlit application."""
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    st.title(PAGE_TITLE)
    st.caption(PAGE_SUBTITLE)

    _render_sidebar()

    tab_pipeline, tab_executor, tab_logs = st.tabs(
        ["Pipeline", "Try the Test Executor", "Run logs"]
    )
    with tab_pipeline:
        _render_pipeline_tab()
    with tab_executor:
        _render_test_executor_tab()
    with tab_logs:
        _render_run_logs_tab()


if __name__ == "__main__":
    main()
