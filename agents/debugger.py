"""Debugger agent stub."""

from __future__ import annotations

from agents.base import BaseAgent
from core.llm import LLMClient
from core.logger import RunLogger
from core.state import WorkflowState


class Debugger(BaseAgent):
    """LLM-powered root-cause diagnosis agent.

    Role:
        LLM agent that analyzes failing test results and localized fault
        regions to formulate root-cause debugging hypotheses.
    Input:
        WorkflowState with `source_code`, `test_results`, `suspect_locations`,
        and optional `review_feedback`.
    Output:
        WorkflowState with populated `hypotheses`.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        logger: RunLogger | None = None,
    ) -> None:
        """Initialize the Debugger LLM agent with injected dependencies."""
        super().__init__(
            name="Debugger",
            agent_type="llm",
            logger=logger,
            llm_client=llm_client,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        """Formulate debugging hypotheses using the LLM (not yet implemented)."""
        raise NotImplementedError("Debugger.run() is not implemented yet.")
