"""Helper functions and constants for the Streamlit UI."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

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

DEFAULT_SAMPLE_CODE: str = """def add(a: int, b: int) -> int:
    \"\"\"Return the sum of a and b (contains an intentional bug).\"\"\"
    return a - b
"""

DEFAULT_SAMPLE_TESTS: str = """from solution import add


def test_add_positive_numbers():
    assert add(2, 3) == 5


def test_add_with_zero():
    assert add(5, 0) == 5
"""

CORRECT_SAMPLE_CODE: str = """def add(a: int, b: int) -> int:
    \"\"\"Return the sum of a and b.\"\"\"
    return a + b
"""

CORRECT_SAMPLE_TESTS: str = """from solution import add


def test_add_positive_numbers():
    assert add(2, 3) == 5


def test_add_with_zero():
    assert add(5, 0) == 5
"""

FAILING_TEST_SAMPLE_CODE: str = """def safe_divide(a: float, b: float) -> float:
    \"\"\"Divide a by b, but forgets to handle division by zero.\"\"\"
    return a / b
"""

FAILING_TEST_SAMPLE_TESTS: str = """from solution import safe_divide


def test_divide_normal():
    assert safe_divide(10, 2) == 5.0


def test_divide_by_zero_returns_zero():
    assert safe_divide(10, 0) == 0.0
"""

# Three built-in sample programs for safe hosted mode (ENABLE_CODE_EXECUTION=False)
BUILTIN_SAMPLES: dict[str, dict[str, str]] = {
    "Buggy program (add subtracts instead of adding)": {
        "code": DEFAULT_SAMPLE_CODE,
        "tests": DEFAULT_SAMPLE_TESTS,
    },
    "Correct program (all tests pass)": {
        "code": CORRECT_SAMPLE_CODE,
        "tests": CORRECT_SAMPLE_TESTS,
    },
    "Failing-test program (unhandled division by zero)": {
        "code": FAILING_TEST_SAMPLE_CODE,
        "tests": FAILING_TEST_SAMPLE_TESTS,
    },
}

AGENT_TYPE_LABELS: dict[str, str] = {
    "llm": "LLM-powered",
    "code": "code-based",
    "tool": "tool-based",
}

# Ordered list of (display_name, agent_class, requires_llm)
AGENT_REGISTRY: list[tuple[str, type[BaseAgent], bool]] = [
    ("Orchestrator", Orchestrator, False),
    ("Analyzer", Analyzer, False),
    ("Test Generator", TestGenerator, True),
    ("Test Executor", TestExecutor, False),
    ("Localizer", Localizer, False),
    ("Debugger", Debugger, True),
    ("Repairer", Repairer, True),
    ("Reviewer", Reviewer, True),
    ("Validator", Validator, False),
    ("Reporter", Reporter, False),
]


def detect_agent_statuses() -> list[dict[str, Any]]:
    """Instantiate all ten agents and detect whether run() is implemented.

    Uses FakeLLMClient and a temporary RunLogger directory so no real LLM or
    API key is ever accessed.
    """
    statuses: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mar_status_check_") as tmp_dir:
        for display_name, agent_cls, requires_llm in AGENT_REGISTRY:
            logger = RunLogger(
                run_id=f"check_{agent_cls.__name__.lower()}",
                base_dir=tmp_dir,
            )
            if requires_llm:
                fake_llm = FakeLLMClient(responses=["status_check"])
                agent = agent_cls(llm_client=fake_llm, logger=logger)
            else:
                agent = agent_cls(logger=logger)

            throwaway_state = WorkflowState(run_id="status_check")
            try:
                agent.run(throwaway_state)
                implemented = True
            except NotImplementedError:
                implemented = False
            except Exception:
                # Any non-NotImplementedError exception means run() has concrete logic
                implemented = True

            statuses.append(
                {
                    "display_name": display_name,
                    "class_name": agent.name,
                    "agent_type": agent.agent_type,
                    "type_label": AGENT_TYPE_LABELS.get(
                        agent.agent_type, agent.agent_type
                    ),
                    "implemented": implemented,
                    "status_badge": (
                        "Implemented" if implemented else "Not implemented yet"
                    ),
                }
            )
    return statuses


def build_pipeline_dot() -> str:
    """Return a Graphviz DOT string representing the supervisor repair workflow."""
    return """
digraph MultiAgentRepairPipeline {
    rankdir=TB;
    node [fontname="Helvetica", fontsize=11, shape=box, style="rounded,filled", margin="0.18,0.10"];
    edge [fontname="Helvetica", fontsize=10, color="#475569"];

    UserInput [label="User Input\\n(Buggy Code & Description)", shape=oval, fillcolor="#F1F5F9", color="#64748B"];
    Orchestrator [label="Orchestrator\\n[code-based]", fillcolor="#DBEAFE", color="#2563EB"];
    Analyzer [label="Analyzer\\n[code-based]", fillcolor="#DBEAFE", color="#2563EB"];
    TestGenerator [label="Test Generator\\n[LLM-powered]", fillcolor="#FEF3C7", color="#D97706"];
    TestExecutor [label="Test Executor\\n[tool-based]", fillcolor="#D1FAE5", color="#059669"];
    InitialCheck [label="Tests pass?", shape=diamond, fillcolor="#F8FAFC", color="#64748B"];
    NoBug [label="No Bug Detected", shape=oval, fillcolor="#DCFCE7", color="#16A34A"];

    Localizer [label="Localizer\\n[code-based]", fillcolor="#DBEAFE", color="#2563EB"];
    Debugger [label="Debugger\\n[LLM-powered]", fillcolor="#FEF3C7", color="#D97706"];
    Repairer [label="Repairer\\n[LLM-powered]", fillcolor="#FEF3C7", color="#D97706"];
    Reviewer [label="Reviewer\\n[LLM-powered]", fillcolor="#FEF3C7", color="#D97706"];
    Validator [label="Validator\\n[code-based]", fillcolor="#DBEAFE", color="#2563EB"];
    ValidationCheck [label="Tests pass?", shape=diamond, fillcolor="#F8FAFC", color="#64748B"];
    Success [label="Repaired (Success)", shape=oval, fillcolor="#DCFCE7", color="#16A34A"];
    Reporter [label="Reporter\\n[code-based]", fillcolor="#DBEAFE", color="#2563EB"];

    UserInput -> Orchestrator;
    Orchestrator -> Analyzer;
    Analyzer -> TestGenerator;
    TestGenerator -> TestExecutor;
    TestExecutor -> InitialCheck;
    InitialCheck -> NoBug [label="Yes"];
    NoBug -> Reporter;
    InitialCheck -> Localizer [label="No (Bug found)"];

    Localizer -> Debugger;
    Debugger -> Repairer;
    Repairer -> Reviewer;
    Reviewer -> Validator;
    Validator -> ValidationCheck;
    ValidationCheck -> Success [label="Yes"];
    Success -> Reporter;
    ValidationCheck -> Localizer [label="No (Retry loop, max 3 attempts)", style=dashed, color="#DC2626"];
    ValidationCheck -> Reporter [label="Max attempts reached (Failed)"];
}
"""


def list_available_runs(runs_dir: str | Path = "runs") -> list[str]:
    """Return sorted run_id folder names in `runs/` that contain a log.jsonl file."""
    base = Path(runs_dir)
    if not base.exists() or not base.is_dir():
        return []
    run_ids = [
        entry.name
        for entry in base.iterdir()
        if entry.is_dir() and (entry / "log.jsonl").exists()
    ]
    return sorted(run_ids)


def load_run_logs(run_id: str, runs_dir: str | Path = "runs") -> list[dict[str, Any]]:
    """Read and return log entries for the given run_id using RunLogger."""
    logger = RunLogger(run_id=run_id, base_dir=runs_dir)
    return logger.read_log()
