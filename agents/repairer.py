"""Repairer agent stub."""

from __future__ import annotations

from agents.base import BaseAgent
from core.llm import LLMClient
from core.logger import RunLogger
from core.state import WorkflowState


class Repairer(BaseAgent):
    """LLM-powered patch generation agent.

    Role:
        LLM agent that generates a candidate code patch (repaired Python source
        code) based on the debugging hypotheses, suspect locations, and any
        reviewer feedback.
    Input:
        WorkflowState with `source_code`, `suspect_locations`, `hypotheses`,
        and optional `review_feedback`.
    Output:
        WorkflowState with updated `current_patch`.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        logger: RunLogger | None = None,
    ) -> None:
        """Initialize the Repairer LLM agent with injected dependencies."""
        super().__init__(
            name="Repairer",
            agent_type="llm",
            logger=logger,
            llm_client=llm_client,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        """Generate a candidate repair patch using the LLM (not yet implemented)."""
        raise NotImplementedError("Repairer.run() is not implemented yet.")
