"""Localizer agent stub."""

from __future__ import annotations

from agents.base import BaseAgent
from core.logger import RunLogger
from core.state import WorkflowState


class Localizer(BaseAgent):
    """Fault localization agent.

    Role:
        Code-based agent that parses failing pytest tracebacks and AST
        structure to pinpoint suspect functions and line numbers in the target
        source code.
    Input:
        WorkflowState with `source_code`, `code_structure`, and failing
        `test_results`.
    Output:
        WorkflowState with populated `suspect_locations`.
    """

    def __init__(self, logger: RunLogger | None = None) -> None:
        """Initialize the Localizer code-based agent."""
        super().__init__(name="Localizer", agent_type="code", logger=logger)

    def run(self, state: WorkflowState) -> WorkflowState:
        """Localize suspect fault locations (not yet implemented)."""
        raise NotImplementedError("Localizer.run() is not implemented yet.")
