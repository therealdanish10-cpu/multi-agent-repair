"""Reviewer agent stub."""

from __future__ import annotations

from agents.base import BaseAgent
from core.llm import LLMClient
from core.logger import RunLogger
from core.state import WorkflowState


class Reviewer(BaseAgent):
    """LLM-powered patch review agent.

    Role:
        LLM agent that inspects the candidate patch for correctness, potential
        regressions, syntax issues, and adherence to the problem description,
        providing structured feedback.
    Input:
        WorkflowState with `source_code`, `current_patch`, `hypotheses`, and
        `generated_tests`.
    Output:
        WorkflowState with updated `review_feedback`.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        logger: RunLogger | None = None,
    ) -> None:
        """Initialize the Reviewer LLM agent with injected dependencies."""
        super().__init__(
            name="Reviewer",
            agent_type="llm",
            logger=logger,
            llm_client=llm_client,
        )

    def run(self, state: WorkflowState) -> WorkflowState:
        """Review the candidate patch using the LLM (not yet implemented)."""
        raise NotImplementedError("Reviewer.run() is not implemented yet.")
