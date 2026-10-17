"""Workflow state definition and status enumeration for the repair pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class WorkflowStatus(str, Enum):
    """Possible lifecycle statuses for a repair workflow run."""

    PENDING = "PENDING"
    NO_BUG = "NO_BUG"
    REPAIRED = "REPAIRED"
    FAILED = "FAILED"
    ERROR = "ERROR"


# Alias for convenience
Status = WorkflowStatus


@dataclass
class WorkflowState:
    """Shared mutable state passed across agents during a repair run."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    source_code: str = ""
    problem_description: str = ""
    code_structure: dict[str, Any] = field(default_factory=dict)
    generated_tests: str = ""
    test_results: dict[str, Any] = field(default_factory=dict)
    suspect_locations: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    current_patch: str = ""
    review_feedback: str = ""
    attempt_counter: int = 0
    max_attempts: int = 3
    status: WorkflowStatus = WorkflowStatus.PENDING
    history: list[dict[str, Any]] = field(default_factory=list)

    def increment_attempt(self) -> int:
        """Increment the repair attempt counter by one and return the new value."""
        self.attempt_counter += 1
        return self.attempt_counter

    def increment_attempt_counter(self) -> int:
        """Alias for increment_attempt()."""
        return self.increment_attempt()

    def record_step(
        self,
        agent_name: str,
        summary: str = "",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record an agent execution step into the workflow history."""
        step: dict[str, Any] = {
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt": self.attempt_counter,
            "summary": summary,
            "details": details or {},
        }
        self.history.append(step)
        return step
