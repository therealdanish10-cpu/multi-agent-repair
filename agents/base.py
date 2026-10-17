"""Abstract base agent class with dependency injection and automatic run logging."""

from __future__ import annotations

import functools
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Literal

from core.llm import LLMClient
from core.logger import RunLogger
from core.state import WorkflowState

AgentType = Literal["llm", "code", "tool"]
VALID_AGENT_TYPES: tuple[AgentType, ...] = ("llm", "code", "tool")


def _wrap_run_with_logging(
    run_fn: Callable[[BaseAgent, WorkflowState], WorkflowState],
) -> Callable[[BaseAgent, WorkflowState], WorkflowState]:
    """Wrap an agent's run(state) method so every invocation is logged."""
    if getattr(run_fn, "_is_logged_wrapper", False):
        return run_fn

    @functools.wraps(run_fn)
    def wrapper(self: BaseAgent, state: WorkflowState) -> WorkflowState:
        start_time = time.perf_counter()
        self._last_prompt = None
        self._last_output = None
        status_val = (
            state.status.value
            if hasattr(state.status, "value")
            else str(state.status)
        )
        input_summary = (
            f"run_id={state.run_id}, status={status_val}, "
            f"attempt={state.attempt_counter}"
        )
        try:
            updated_state = run_fn(self, state)
            duration = time.perf_counter() - start_time
            if self.logger is not None:
                out_status = (
                    updated_state.status.value
                    if hasattr(updated_state.status, "value")
                    else str(updated_state.status)
                )
                raw_out = (
                    self._last_output
                    if self._last_output is not None
                    else f"completed (status={out_status})"
                )
                self.logger.log_interaction(
                    agent_name=self.name,
                    input_summary=input_summary,
                    prompt=self._last_prompt,
                    raw_output=raw_out,
                    duration=duration,
                )
            return updated_state
        except Exception as exc:
            duration = time.perf_counter() - start_time
            if self.logger is not None:
                self.logger.log_interaction(
                    agent_name=self.name,
                    input_summary=input_summary,
                    prompt=self._last_prompt,
                    raw_output=f"{type(exc).__name__}: {exc}",
                    duration=duration,
                )
            raise

    setattr(wrapper, "_is_logged_wrapper", True)
    return wrapper


class BaseAgent(ABC):
    """Abstract base class for all agents in the multi-agent-repair system."""

    __test__: bool = False
    name: str
    agent_type: AgentType

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Automatically wrap subclass run() implementations with logging."""
        super().__init_subclass__(**kwargs)
        if "run" in cls.__dict__ and not getattr(
            cls.__dict__["run"], "__isabstractmethod__", False
        ):
            setattr(cls, "run", _wrap_run_with_logging(cls.__dict__["run"]))

    def __init__(
        self,
        name: str,
        agent_type: AgentType,
        logger: RunLogger | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        """Initialize the base agent with name, type, logger, and optional LLM client."""
        if agent_type not in VALID_AGENT_TYPES:
            raise ValueError(
                f"Invalid agent_type {agent_type!r}. Must be one of {VALID_AGENT_TYPES}."
            )
        self.name = name
        self.agent_type = agent_type
        self.logger = logger
        self.llm_client = llm_client
        self._last_prompt: str | None = None
        self._last_output: str | None = None

    def _generate_with_llm(self, prompt: str, system: str | None = None) -> str:
        """Helper for LLM agents to invoke the injected LLMClient and track I/O."""
        if self.llm_client is None:
            raise ValueError(f"Agent {self.name!r} requires an injected LLMClient.")
        self._last_prompt = prompt
        response = self.llm_client.generate(prompt=prompt, system=system)
        self._last_output = response
        return response

    @abstractmethod
    def run(self, state: WorkflowState) -> WorkflowState:
        """Execute the agent's task on the given workflow state and return it."""
        raise NotImplementedError
