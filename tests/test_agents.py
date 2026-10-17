"""Tests for BaseAgent and the ten agent stubs."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents import (
    Analyzer,
    BaseAgent,
    Debugger,
    Localizer,
    Orchestrator,
    Repairer,
    Reporter,
    Reviewer,
    TestExecutor,
    TestGenerator,
    Validator,
)
from core.llm import FakeLLMClient
from core.logger import RunLogger
from core.state import WorkflowState


class DummyConcreteAgent(BaseAgent):
    """Concrete agent used to verify automatic run() logging on BaseAgent."""

    def __init__(self, llm_client: FakeLLMClient, logger: RunLogger) -> None:
        super().__init__(
            name="DummyConcreteAgent",
            agent_type="llm",
            logger=logger,
            llm_client=llm_client,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        reply = self._generate_with_llm("Analyze code")
        state.record_step(self.name, summary=reply)
        return state


def test_base_agent_logs_every_run_call(tmp_path: Path) -> None:
    """Verify BaseAgent automatically logs every run() execution to RunLogger."""
    logger = RunLogger(run_id="run-log-test", base_dir=tmp_path)
    fake_llm = FakeLLMClient(responses=["Looks good"])
    agent = DummyConcreteAgent(llm_client=fake_llm, logger=logger)

    state = WorkflowState(run_id="run-log-test", source_code="x = 1")
    updated = agent.run(state)

    assert len(updated.history) == 1
    logs = logger.read_log()
    assert len(logs) == 1
    assert logs[0]["agent_name"] == "DummyConcreteAgent"
    assert logs[0]["prompt"] == "Analyze code"
    assert logs[0]["raw_output"] == "Looks good"
    assert isinstance(logs[0]["duration"], float)


@pytest.mark.parametrize(
    ("agent_cls", "expected_name", "expected_type", "is_llm"),
    [
        (Orchestrator, "Orchestrator", "code", False),
        (Analyzer, "Analyzer", "code", False),
        (TestGenerator, "TestGenerator", "llm", True),
        (TestExecutor, "TestExecutor", "tool", False),
        (Localizer, "Localizer", "code", False),
        (Debugger, "Debugger", "llm", True),
        (Repairer, "Repairer", "llm", True),
        (Reviewer, "Reviewer", "llm", True),
        (Validator, "Validator", "code", False),
        (Reporter, "Reporter", "code", False),
    ],
)
def test_all_ten_agent_stubs(
    tmp_path: Path,
    agent_cls: type[BaseAgent],
    expected_name: str,
    expected_type: str,
    is_llm: bool,
) -> None:
    """Verify each of the 10 agent stubs has the right name, type, and raises NotImplementedError."""
    logger = RunLogger(run_id=f"run-{expected_name.lower()}", base_dir=tmp_path)
    fake_llm = FakeLLMClient(responses=["stub"])

    if is_llm:
        agent = agent_cls(llm_client=fake_llm, logger=logger)
        assert agent.llm_client is fake_llm
    else:
        agent = agent_cls(logger=logger)

    assert agent.name == expected_name
    assert agent.agent_type == expected_type
    assert agent.__doc__ is not None and len(agent.__doc__.strip()) > 0

    state = WorkflowState(run_id=f"run-{expected_name.lower()}")
    with pytest.raises(NotImplementedError):
        agent.run(state)

    # Even stub calls raising NotImplementedError are logged by BaseAgent
    logs = logger.read_log()
    assert len(logs) == 1
    assert logs[0]["agent_name"] == expected_name
