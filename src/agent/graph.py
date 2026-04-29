"""
Drug Discovery LangGraph StateGraph.

Topology:
  START → orchestrator
  orchestrator → tools          (regular tool calls)
  orchestrator → target_evaluator | controls_generator |
                 screening_designer | hits_analyzer    (delegation)
  orchestrator → END            (direct response, no tool calls)
  tools        → orchestrator   (loop until no more tool calls)
  *_sub_agent  → synthesizer    (Haiku formats the result for the user)
  synthesizer  → END

LangSmith tracing is enabled automatically when LANGCHAIN_TRACING_V2=true
and LANGCHAIN_API_KEY are set in the environment.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.agent.nodes.orchestrator import (
    ORCHESTRATOR_TOOLS,
    orchestrator_node,
    route_after_orchestrator,
)
from src.agent.nodes.sub_agents import (
    controls_generator_node,
    hits_analyzer_node,
    screening_designer_node,
    target_evaluator_node,
)
from src.agent.nodes.synthesizer import synthesizer_node
from src.agent.state import ResearchState

# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------

_builder = StateGraph(ResearchState)

# Nodes
_builder.add_node("orchestrator", orchestrator_node)
_builder.add_node("tools", ToolNode(tools=ORCHESTRATOR_TOOLS))
_builder.add_node("target_evaluator", target_evaluator_node)
_builder.add_node("controls_generator", controls_generator_node)
_builder.add_node("screening_designer", screening_designer_node)
_builder.add_node("hits_analyzer", hits_analyzer_node)
_builder.add_node("synthesizer", synthesizer_node)

# Entry point
_builder.set_entry_point("orchestrator")

# Conditional routing from orchestrator
_builder.add_conditional_edges(
    "orchestrator",
    route_after_orchestrator,
    {
        "tools": "tools",
        "target_evaluator": "target_evaluator",
        "controls_generator": "controls_generator",
        "screening_designer": "screening_designer",
        "hits_analyzer": "hits_analyzer",
        "end": END,
    },
)

# Tools loop back to orchestrator
_builder.add_edge("tools", "orchestrator")

# Sub-agents always flow to synthesizer
_builder.add_edge("target_evaluator", "synthesizer")
_builder.add_edge("controls_generator", "synthesizer")
_builder.add_edge("screening_designer", "synthesizer")
_builder.add_edge("hits_analyzer", "synthesizer")

# Synthesizer ends the turn
_builder.add_edge("synthesizer", END)


def build_graph(checkpointer=None):
    """Compile and return the runnable graph.

    Pass a checkpointer to enable conversation persistence across turns.
    """
    return _builder.compile(checkpointer=checkpointer)
