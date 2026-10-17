"""Unit tests for the TestExecutor agent in agents/test_executor.py."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

import core.config as config
from agents.test_executor import MAX_OUTPUT_CHARS, TRUNCATION_MARKER, TestExecutor
from core.logger import RunLogger
from core.state import WorkflowState

EXPECTED_RESULT_KEYS = {
    "passed",
    "num_passed",
    "num_failed",
    "num_errors",
    "num_tests",
    "timed_out",
    "duration_seconds",
    "failures",
    "stdout",
    "stderr",
    "return_code",
}


def test_passing_code_returns_passed_true() -> None:
    """Correct code with passing tests returns passed=True and all expected keys."""
    executor = TestExecutor()
    code = (
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )
    tests = (
        "from solution import add\n\n"
        "def test_add_positive():\n"
        "    assert add(2, 3) == 5\n\n"
        "def test_add_negative():\n"
        "    assert add(-1, -4) == -5\n"
    )

    result = executor.execute(code, tests)

    assert set(result.keys()) == EXPECTED_RESULT_KEYS
    assert result["passed"] is True
    assert result["num_passed"] == 2
    assert result["num_failed"] == 0
    assert result["num_errors"] == 0
    assert result["num_tests"] == 2
    assert result["timed_out"] is False
    assert result["failures"] == []
    assert result["return_code"] == 0
    assert isinstance(result["duration_seconds"], float)


def test_failing_assertion_returns_failure_details() -> None:
    """A failing assertion returns passed=False with test_name and message in failures."""
    executor = TestExecutor()
    code = (
        "def multiply(a: int, b: int) -> int:\n"
        "    return a + b  # Bug: addition instead of multiplication\n"
    )
    tests = (
        "from solution import multiply\n\n"
        "def test_multiply_basic():\n"
        "    assert multiply(3, 4) == 12\n"
    )

    result = executor.execute(code, tests)

    assert set(result.keys()) == EXPECTED_RESULT_KEYS
    assert result["passed"] is False
    assert result["num_passed"] == 0
    assert result["num_failed"] == 1
    assert result["num_errors"] == 0
    assert result["num_tests"] == 1
    assert result["timed_out"] is False
    assert len(result["failures"]) == 1
    failure = result["failures"][0]
    assert failure["test_name"] == "test_multiply_basic"
    assert "assert" in failure["message"] or "12" in failure["message"]
    assert "multiply(3, 4)" in failure["traceback"]


def test_infinite_loop_times_out_quickly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Code with an infinite loop is killed on timeout and returns timed_out=True."""
    monkeypatch.setattr(config, "TEST_TIMEOUT_SECONDS", 2)
    executor = TestExecutor(timeout_seconds=2)

    code = (
        "def loop_forever() -> int:\n"
        "    while True:\n"
        "        pass\n"
        "    return 1\n"
    )
    tests = (
        "from solution import loop_forever\n\n"
        "def test_loop():\n"
        "    assert loop_forever() == 1\n"
    )

    start = time.perf_counter()
    result = executor.execute(code, tests)
    elapsed = time.perf_counter() - start

    assert set(result.keys()) == EXPECTED_RESULT_KEYS
    assert result["timed_out"] is True
    assert result["passed"] is False
    assert elapsed < 8.0


def test_syntax_error_in_solution_reported_as_error() -> None:
    """A syntax error in solution.py is reported as an error rather than crashing."""
    executor = TestExecutor()
    code = "def broken_syntax(a, b)\n    return a + b\n"
    tests = (
        "from solution import broken_syntax\n\n"
        "def test_broken():\n"
        "    assert broken_syntax(1, 2) == 3\n"
    )

    result = executor.execute(code, tests)

    assert set(result.keys()) == EXPECTED_RESULT_KEYS
    assert result["passed"] is False
    assert result["num_errors"] >= 1
    assert len(result["failures"]) >= 1
    combined = (
        result["failures"][0]["message"] + "\n" + result["failures"][0]["traceback"]
    )
    assert "SyntaxError" in combined or "collection failure" in combined


def test_import_error_reported_as_error() -> None:
    """Importing a non-existent function from solution.py is reported as an error."""
    executor = TestExecutor()
    code = "def existing_fn() -> int:\n    return 42\n"
    tests = (
        "from solution import non_existent_fn\n\n"
        "def test_missing_import():\n"
        "    assert non_existent_fn() == 42\n"
    )

    result = executor.execute(code, tests)

    assert set(result.keys()) == EXPECTED_RESULT_KEYS
    assert result["passed"] is False
    assert result["num_errors"] >= 1
    assert len(result["failures"]) >= 1
    combined = (
        result["failures"][0]["message"] + "\n" + result["failures"][0]["traceback"]
    )
    assert "ImportError" in combined or "non_existent_fn" in combined


def test_secret_isolation_excludes_gemini_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Subprocess environment does not inherit GEMINI_API_KEY from parent process."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake_secret_key_for_isolation_test")
    executor = TestExecutor()

    code = (
        "import os\n\n"
        "def get_env_keys() -> list[str]:\n"
        "    return list(os.environ.keys())\n"
    )
    tests = (
        "import os\n"
        "from solution import get_env_keys\n\n"
        "def test_gemini_api_key_not_leaked():\n"
        "    assert 'GEMINI_API_KEY' not in os.environ\n"
        "    assert 'GEMINI_API_KEY' not in get_env_keys()\n"
    )

    result = executor.execute(code, tests)

    assert result["passed"] is True
    assert result["num_passed"] == 1
    assert result["num_failed"] == 0
    assert result["num_errors"] == 0


def test_output_truncation_for_large_stdout() -> None:
    """Stdout exceeding 20,000 characters is truncated and ends with the marker."""
    executor = TestExecutor()
    code = (
        "def noisy() -> int:\n"
        "    print('X' * 35000)\n"
        "    return 1\n"
    )
    tests = (
        "from solution import noisy\n\n"
        "def test_noisy():\n"
        "    assert noisy() == 1\n"
    )

    result = executor.execute(code, tests)

    assert result["passed"] is True
    assert len(result["stdout"]) == MAX_OUTPUT_CHARS
    assert result["stdout"].endswith(TRUNCATION_MARKER)


def test_temporary_directory_is_removed_after_execution() -> None:
    """The temporary directory created during execute() is deleted afterwards."""
    executor = TestExecutor()
    code = "def f() -> int:\n    return 7\n"
    tests = "from solution import f\n\ndef test_f():\n    assert f() == 7\n"

    result = executor.execute(code, tests)

    assert result["passed"] is True
    assert executor.last_temp_dir is not None
    assert not executor.last_temp_dir.exists()


def test_run_stores_test_results_in_state_and_logs(tmp_path: Path) -> None:
    """run(state) executes tests, writes state.test_results, and logs the run."""
    logger = RunLogger(run_id="run-exec-1", base_dir=tmp_path)
    executor = TestExecutor(logger=logger)

    state = WorkflowState(
        run_id="run-exec-1",
        source_code="def square(n: int) -> int:\n    return n * n\n",
        generated_tests=(
            "from solution import square\n\n"
            "def test_square():\n"
            "    assert square(5) == 25\n"
        ),
    )

    updated = executor.run(state)

    assert updated is state
    assert updated.test_results["passed"] is True
    assert updated.test_results["num_passed"] == 1
    logs = logger.read_log()
    assert len(logs) == 1
    assert logs[0]["agent_name"] == "TestExecutor"


def test_run_handles_empty_generated_tests_without_running_pytest(
    tmp_path: Path,
) -> None:
    """run(state) sets a clear error result when generated_tests is empty."""
    logger = RunLogger(run_id="run-empty-tests", base_dir=tmp_path)
    executor = TestExecutor(logger=logger)

    state = WorkflowState(
        run_id="run-empty-tests",
        source_code="def square(n: int) -> int:\n    return n * n\n",
        generated_tests="   ",
    )

    updated = executor.run(state)

    assert set(updated.test_results.keys()) == EXPECTED_RESULT_KEYS
    assert updated.test_results["passed"] is False
    assert updated.test_results["num_errors"] == 1
    assert updated.test_results["num_tests"] == 0
    assert len(updated.test_results["failures"]) == 1
    assert "No generated tests" in updated.test_results["failures"][0]["message"]
    assert executor.last_temp_dir is None
