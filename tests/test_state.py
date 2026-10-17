"""Tests for WorkflowState and WorkflowStatus in core.state."""

from __future__ import annotations

from core.state import WorkflowState, WorkflowStatus


def test_workflow_state_defaults() -> None:
    """Verify default field values and status enum on a new WorkflowState."""
    state = WorkflowState(
        run_id="run-001",
        source_code="def add(a, b): return a - b",
        problem_description="Add two numbers",
    )
    assert state.run_id == "run-001"
    assert state.source_code == "def add(a, b): return a - b"
    assert state.problem_description == "Add two numbers"
    assert state.code_structure == {}
    assert state.generated_tests == ""
    assert state.test_results == {}
    assert state.suspect_locations == []
    assert state.hypotheses == []
    assert state.current_patch == ""
    assert state.review_feedback == ""
    assert state.attempt_counter == 0
    assert state.max_attempts == 3
    assert state.status == WorkflowStatus.PENDING
    assert state.history == []


def test_workflow_status_enum_values() -> None:
    """Verify all required status enum members exist."""
    expected = {"PENDING", "NO_BUG", "REPAIRED", "FAILED", "ERROR"}
    actual = {member.name for member in WorkflowStatus}
    assert actual == expected


def test_increment_attempt_helper() -> None:
    """Verify increment_attempt increments and returns the attempt counter."""
    state = WorkflowState(run_id="run-002")
    assert state.attempt_counter == 0
    assert state.increment_attempt() == 1
    assert state.attempt_counter == 1
    assert state.increment_attempt() == 2
    assert state.attempt_counter == 2


def test_record_step_helper() -> None:
    """Verify record_step appends structured entries to history."""
    state = WorkflowState(run_id="run-003")
    state.increment_attempt()

    step = state.record_step(
        agent_name="Analyzer",
        summary="Parsed AST for 1 function",
        details={"functions": ["add"]},
    )

    assert len(state.history) == 1
    assert state.history[0] == step
    assert step["agent_name"] == "Analyzer"
    assert step["attempt"] == 1
    assert step["summary"] == "Parsed AST for 1 function"
    assert step["details"] == {"functions": ["add"]}
    assert "timestamp" in step
