"""Tests for LangGraph graph structure and routing logic."""

import pytest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.agent.graph import build_graph
from src.agent.nodes.orchestrator import route_after_orchestrator
from src.agent.state import ResearchState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_state(**overrides) -> dict:
    base = {
        "messages": [],
        "research_session_id": "rs-test-001",
        "auth_session_id": "auth-test-001",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "pipeline_stage": "idle",
        "delegate_to": None,
        "sub_agent_output": None,
        "orchestrator_turns": 0,
    }
    base.update(overrides)
    return base


def _ai_message_with_tool_call(tool_name: str, args: dict) -> AIMessage:
    msg = AIMessage(content="")
    msg.tool_calls = [{"name": tool_name, "args": args, "id": "tc-001"}]
    return msg


# ---------------------------------------------------------------------------
# Graph structure tests
# ---------------------------------------------------------------------------

class TestBuildGraph:
    def test_graph_compiles_without_checkpointer(self):
        graph = build_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_graph()
        node_names = set(graph.nodes.keys())
        assert "orchestrator" in node_names
        assert "tools" in node_names
        assert "target_evaluator" in node_names
        assert "controls_generator" in node_names
        assert "screening_designer" in node_names
        assert "hits_analyzer" in node_names
        assert "synthesizer" in node_names


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------

class TestRouteAfterOrchestrator:
    def test_no_tool_calls_routes_to_end(self):
        state = _base_state(messages=[AIMessage(content="Here is my answer.")])
        result = route_after_orchestrator(state)
        assert result == "end"

    def test_regular_tool_call_routes_to_tools(self):
        msg = _ai_message_with_tool_call("uniprot_search", {"query": "GyrB"})
        state = _base_state(messages=[msg])
        result = route_after_orchestrator(state)
        assert result == "tools"

    def test_delegation_routes_to_target_evaluator(self):
        msg = _ai_message_with_tool_call(
            "delegate_to_sub_agent",
            {"agent_name": "target_evaluator", "task_description": "Evaluate GyrB"},
        )
        state = _base_state(messages=[msg])
        result = route_after_orchestrator(state)
        assert result == "target_evaluator"

    def test_delegation_routes_to_controls_generator(self):
        msg = _ai_message_with_tool_call(
            "delegate_to_sub_agent",
            {"agent_name": "controls_generator", "task_description": "Find inhibitors"},
        )
        state = _base_state(messages=[msg])
        result = route_after_orchestrator(state)
        assert result == "controls_generator"

    def test_delegation_routes_to_screening_designer(self):
        msg = _ai_message_with_tool_call(
            "delegate_to_sub_agent",
            {"agent_name": "screening_designer", "task_description": "Design pharmacophore"},
        )
        state = _base_state(messages=[msg])
        result = route_after_orchestrator(state)
        assert result == "screening_designer"

    def test_delegation_routes_to_hits_analyzer(self):
        msg = _ai_message_with_tool_call(
            "delegate_to_sub_agent",
            {"agent_name": "hits_analyzer", "task_description": "Rank hits"},
        )
        state = _base_state(messages=[msg])
        result = route_after_orchestrator(state)
        assert result == "hits_analyzer"

    def test_empty_messages_routes_to_end(self):
        state = _base_state(messages=[])
        result = route_after_orchestrator(state)
        assert result == "end"

    def test_turn_cap_routes_to_end(self):
        """Orchestrator hard-cap at 6 turns prevents runaway loops."""
        msg = _ai_message_with_tool_call("uniprot_search", {"query": "GyrB"})
        state = _base_state(messages=[msg], orchestrator_turns=6)
        result = route_after_orchestrator(state)
        assert result == "end"

    def test_turn_cap_not_triggered_below_limit(self):
        msg = _ai_message_with_tool_call("uniprot_search", {"query": "GyrB"})
        state = _base_state(messages=[msg], orchestrator_turns=5)
        result = route_after_orchestrator(state)
        assert result == "tools"


# ---------------------------------------------------------------------------
# ResearchState structure
# ---------------------------------------------------------------------------

class TestResearchState:
    def test_state_accepts_all_required_fields(self):
        state = _base_state()
        assert state["pipeline_stage"] == "idle"
        assert state["delegate_to"] is None
        assert state["sub_agent_output"] is None
        assert state["orchestrator_turns"] == 0

    def test_state_messages_accepts_langchain_messages(self):
        msgs = [
            HumanMessage(content="Evaluate GyrB"),
            AIMessage(content="I'll look that up."),
        ]
        state = _base_state(messages=msgs)
        assert len(state["messages"]) == 2
        assert state["messages"][0].content == "Evaluate GyrB"
