"""Tool-based TestExecutor agent for running pytest in an isolated subprocess.

Security Note:
    Running untrusted code in a restricted subprocess with a filtered
    environment and timeout is NOT a full security boundary. Full container
    isolation using Docker is planned for a later phase of the project.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import core.config as config
from agents.base import BaseAgent
from core.logger import RunLogger
from core.state import WorkflowState

MAX_OUTPUT_CHARS: int = 20_000
TRUNCATION_MARKER: str = "...[truncated]"

# Strict allowlist of OS environment variables needed for Python/pytest to run
# on Windows and POSIX without leaking secrets such as GEMINI_API_KEY.
_ALLOWED_ENV_VARS: tuple[str, ...] = (
    "PATH",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "PATHEXT",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "APPDATA",
    "HOME",
    "LANG",
    "LC_ALL",
)


def _build_restricted_env() -> dict[str, str]:
    """Build a minimal environment dict that excludes API keys and secrets."""
    env: dict[str, str] = {}
    for key in _ALLOWED_ENV_VARS:
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_ADDOPTS"] = "--capture=tee-sys"
    return env


def _truncate_output(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """Truncate text to at most max_chars, appending TRUNCATION_MARKER when cut."""
    if len(text) <= max_chars:
        return text
    keep_len = max(0, max_chars - len(TRUNCATION_MARKER))
    return text[:keep_len] + TRUNCATION_MARKER


def _decode_stream(data: str | bytes | None) -> str:
    """Convert subprocess stream output (str, bytes, or None) into a string."""
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data


def _kill_process_tree(proc: subprocess.Popen[Any]) -> None:
    """Forcefully terminate a subprocess and all of its child processes."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    try:
        proc.kill()
    except OSError:
        pass


def _extract_concise_error_line(traceback_text: str) -> str:
    """Extract the most informative error line from a pytest traceback."""
    lines = [line.strip() for line in traceback_text.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("E   "):
            return line[4:].strip()
    return lines[-1] if lines else ""


def _parse_junit_xml(
    xml_path: Path,
) -> tuple[int, int, int, int, list[dict[str, str]]] | None:
    """Parse pytest JUnit XML into (passed, failed, errors, total, failures).

    Returns None if the XML file does not exist or cannot be parsed.
    """
    if not xml_path.exists():
        return None

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError:
        return None

    num_passed = 0
    num_failed = 0
    num_errors = 0
    failures: list[dict[str, str]] = []

    for testcase in root.iter("testcase"):
        test_name = (
            testcase.attrib.get("name")
            or testcase.attrib.get("classname")
            or "test_solution"
        )
        failure_elems = testcase.findall("failure")
        error_elems = testcase.findall("error")
        skipped_elems = testcase.findall("skipped")

        if failure_elems:
            num_failed += 1
            for fail in failure_elems:
                raw_msg = fail.attrib.get("message", "").strip()
                tb_text = (fail.text or "").strip()
                message = raw_msg or _extract_concise_error_line(tb_text) or "Test failed"
                failures.append(
                    {
                        "test_name": test_name,
                        "message": message,
                        "traceback": tb_text,
                    }
                )
        elif error_elems:
            num_errors += 1
            for err in error_elems:
                raw_msg = err.attrib.get("message", "").strip()
                tb_text = (err.text or "").strip()
                detail = _extract_concise_error_line(tb_text)
                if raw_msg and detail and detail not in raw_msg:
                    message = f"{raw_msg}: {detail}"
                else:
                    message = raw_msg or detail or "Test collection/execution error"
                failures.append(
                    {
                        "test_name": test_name,
                        "message": message,
                        "traceback": tb_text,
                    }
                )
        elif skipped_elems:
            continue
        else:
            num_passed += 1

    num_tests = num_passed + num_failed + num_errors
    return num_passed, num_failed, num_errors, num_tests, failures


class TestExecutor(BaseAgent):
    """Tool-based pytest execution agent.

    Role:
        Tool-based agent that runs the generated pytest suite against the
        target program (or candidate patch) with a timeout and captures real
        pytest execution results.
    Input:
        WorkflowState with `source_code` and `generated_tests`.
    Output:
        WorkflowState with populated `test_results`.
    """

    __test__: bool = False

    def __init__(
        self,
        logger: RunLogger | None = None,
        timeout_seconds: float | int | None = None,
    ) -> None:
        """Initialize the TestExecutor tool-based agent."""
        super().__init__(name="TestExecutor", agent_type="tool", logger=logger)
        self.timeout_seconds: float | None = (
            float(timeout_seconds) if timeout_seconds is not None else None
        )
        self.last_temp_dir: Path | None = None

    def _get_timeout(self) -> float:
        """Return the configured timeout in seconds."""
        if self.timeout_seconds is not None:
            return float(self.timeout_seconds)
        return float(config.TEST_TIMEOUT_SECONDS)

    def execute(self, code: str, tests: str) -> dict[str, Any]:
        """Run pytest on `code` and `tests` inside an isolated temporary folder.

        Does not modify any WorkflowState so it can be reused by Validator.
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="multi_agent_repair_"))
        self.last_temp_dir = temp_dir
        start_time = time.perf_counter()

        timed_out = False
        raw_stdout = ""
        raw_stderr = ""
        return_code = -1

        try:
            solution_file = temp_dir / "solution.py"
            test_file = temp_dir / "test_solution.py"
            xml_file = temp_dir / "result.xml"

            solution_file.write_text(code, encoding="utf-8")
            test_file.write_text(tests, encoding="utf-8")

            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "test_solution.py",
                "-q",
                "--tb=short",
                "-p",
                "no:cacheprovider",
                "--junitxml=result.xml",
            ]
            env = _build_restricted_env()
            timeout = self._get_timeout()

            proc = subprocess.Popen(
                cmd,
                cwd=str(temp_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            try:
                out, err = proc.communicate(timeout=timeout)
                raw_stdout = _decode_stream(out)
                raw_stderr = _decode_stream(err)
                return_code = proc.returncode if proc.returncode is not None else -1
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                _kill_process_tree(proc)
                try:
                    out_after, err_after = proc.communicate(timeout=2.0)
                    raw_stdout = _decode_stream(exc.stdout) + _decode_stream(out_after)
                    raw_stderr = _decode_stream(exc.stderr) + _decode_stream(err_after)
                except Exception:
                    raw_stdout = _decode_stream(exc.stdout)
                    raw_stderr = _decode_stream(exc.stderr)
                return_code = -1

            duration = time.perf_counter() - start_time
            stdout_truncated = _truncate_output(raw_stdout)
            stderr_truncated = _truncate_output(raw_stderr)

            parsed = _parse_junit_xml(xml_file)
            if parsed is not None:
                num_passed, num_failed, num_errors, num_tests, failures = parsed
            else:
                num_passed = 0
                num_failed = 0
                num_errors = 0
                num_tests = 0
                failures = []

            if timed_out:
                if not failures:
                    failures.append(
                        {
                            "test_name": "test_solution",
                            "message": f"Test execution timed out after {timeout}s",
                            "traceback": stderr_truncated or stdout_truncated,
                        }
                    )
            elif return_code != 0 and num_failed == 0 and num_errors == 0:
                # Fallback if pytest exited non-zero without writing error entries to XML
                num_errors = 1
                combined_output = (raw_stderr or raw_stdout).strip()
                concise = _extract_concise_error_line(combined_output)
                failures.append(
                    {
                        "test_name": "test_solution",
                        "message": concise or "Pytest collection or execution error",
                        "traceback": _truncate_output(combined_output),
                    }
                )

            passed = (
                not timed_out
                and return_code == 0
                and num_tests >= 1
                and num_passed >= 1
                and num_failed == 0
                and num_errors == 0
            )

            return {
                "passed": passed,
                "num_passed": num_passed,
                "num_failed": num_failed,
                "num_errors": num_errors,
                "num_tests": num_tests,
                "timed_out": timed_out,
                "duration_seconds": round(duration, 6),
                "failures": failures,
                "stdout": stdout_truncated,
                "stderr": stderr_truncated,
                "return_code": return_code,
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def run(self, state: WorkflowState) -> WorkflowState:
        """Execute generated tests against state.source_code and store results."""
        if not state.generated_tests or not state.generated_tests.strip():
            error_msg = "No generated tests provided in state.generated_tests."
            state.test_results = {
                "passed": False,
                "num_passed": 0,
                "num_failed": 0,
                "num_errors": 1,
                "num_tests": 0,
                "timed_out": False,
                "duration_seconds": 0.0,
                "failures": [
                    {
                        "test_name": "test_solution",
                        "message": error_msg,
                        "traceback": "",
                    }
                ],
                "stdout": "",
                "stderr": error_msg,
                "return_code": -1,
            }
            self._last_output = f"error: {error_msg}"
            return state

        results = self.execute(state.source_code, state.generated_tests)
        state.test_results = results
        self._last_output = (
            f"passed={results['passed']}, "
            f"num_passed={results['num_passed']}, "
            f"num_failed={results['num_failed']}, "
            f"num_errors={results['num_errors']}, "
            f"timed_out={results['timed_out']}"
        )
        return state
