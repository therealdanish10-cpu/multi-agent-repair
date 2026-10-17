"""Reporter agent stub."""

from __future__ import annotations

from agents.base import BaseAgent
from core.logger import RunLogger
from core.state import WorkflowState


class Reporter(BaseAgent):
    """Final report generation agent.

    Role:
        Code-based agent that compiles the final summary of the repair run,
        including test outcomes, attempted patches, number of attempts used,
        and final repair status.
    Input:
        WorkflowState with final `status`, `attempt_counter`, `current_patch`,
        `test_results`, and `history`.
    Output:
        WorkflowState with the final report step recorded in `history`.
    """

    def __init__(self, logger: RunLogger | None = None) -> None:
        """Initialize the Reporter code-based agent."""
        super().__init__(name="Reporter", agent_type="code", logger=logger)

    def run(self, state: WorkflowState) -> WorkflowState:
        """Compile final repair summary report (not yet implemented)."""
        raise NotImplementedError("Reporter.run() is not implemented yet.")
