"""LangGraph agent state shared across all nodes."""

from __future__ import annotations

from typing import Annotated, Optional, Sequence
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ResearchState(TypedDict):
    """Full state passed through every node in the research graph."""

    # Conversation messages — add_messages reducer appends rather than overwrites
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Auth / session identifiers
    research_session_id: str
    auth_session_id: str
    provider: str
    model: str

    # Which pipeline stage the session is currently in
    # Values: "idle" | "evaluate" | "controls" | "screening" | "hits"
    pipeline_stage: str

    # Set by the orchestrator when it wants to delegate to a Nemotron sub-agent.
    # Cleared to None after the sub-agent completes.
    delegate_to: Optional[str]

    # Raw structured output from the last sub-agent run — consumed by synthesizer.
    sub_agent_output: Optional[dict]
