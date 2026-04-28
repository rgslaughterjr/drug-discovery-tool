"""
Orchestrator node — Claude Sonnet as the reasoning brain.

Receives the full conversation, decides whether to:
  1. Call a domain tool directly (→ ToolNode)
  2. Delegate to a Nemotron sub-agent  (→ sub-agent node)
  3. Answer directly or ask for clarification (→ END)
"""

from __future__ import annotations

import os
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode

from src.agent.nodes.tools import ALL_TOOLS
from src.agent.state import ResearchState

_ORCHESTRATOR_SYSTEM = """\
You are an expert drug discovery orchestrator. You help university researchers through a \
four-step pipeline: (1) Evaluate Target, (2) Generate Controls, (3) Prepare Screening, \
(4) Analyze Hits.

You have access to real databases (PubChem, ChEMBL, UniProt, RCSB PDB) and local RDKit tools. \
NEVER hallucinate compound data — always call the appropriate tool to verify.

For complex multi-tool scientific workflows, delegate to the appropriate sub-agent using \
delegate_to_sub_agent. Sub-agents are specialized Nemotron models with focused tool subsets:
  • target_evaluator  — UniProt + PDB druggability assessment
  • controls_generator — ChEMBL + PubChem IC50-verified controls + decoys
  • screening_designer — PDB binding site pharmacophore design
  • hits_analyzer      — virtual screening hit prioritization + PAINS/scaffold analysis

Keep your responses concise. Use structured_result for tabular compound data.
Do not repeat information the user already provided.
"""

# Delegation tool schema — a synthetic tool that routes to a sub-agent node
from langchain_core.tools import tool
from typing import Optional


@tool
def delegate_to_sub_agent(
    agent_name: Literal[
        "target_evaluator",
        "controls_generator",
        "screening_designer",
        "hits_analyzer",
    ],
    task_description: str,
    context: Optional[dict] = None,
) -> str:
    """Delegate a complex scientific workflow step to a specialized Nemotron sub-agent.

    Use when a pipeline step requires multi-tool scientific reasoning across multiple databases.
    agent_name: 'target_evaluator' | 'controls_generator' | 'screening_designer' | 'hits_analyzer'
    task_description: plain-language description of the task for the sub-agent.
    context: optional dict with known IDs (uniprot_id, pdb_id, chembl_target_id, etc.)
    """
    # The actual routing happens in the graph edge; this function is never called directly.
    # It exists so the LLM can produce a tool_call that the router detects.
    return f"Delegating to {agent_name}: {task_description}"


ORCHESTRATOR_TOOLS = ALL_TOOLS + [delegate_to_sub_agent]
_DELEGATION_TOOL_NAMES = {
    "target_evaluator", "controls_generator", "screening_designer", "hits_analyzer",
}


def _build_llm(api_key: str, model: str) -> ChatAnthropic:
    return ChatAnthropic(
        model=model,
        api_key=api_key,
        max_tokens=4096,
        temperature=0,
    ).bind_tools(ORCHESTRATOR_TOOLS)


def orchestrator_node(state: ResearchState) -> dict:
    """Invoke Sonnet with the full conversation; return state update."""
    api_key = state.get("_anthropic_api_key") or os.environ["ANTHROPIC_API_KEY"]
    model = state.get("model") or os.getenv("ORCHESTRATOR_MODEL", "claude-sonnet-4-6")

    llm = _build_llm(api_key, model)

    messages = [SystemMessage(content=_ORCHESTRATOR_SYSTEM)] + list(state["messages"])
    response = llm.invoke(messages)

    # Check if this is a delegation call — extract the target sub-agent name
    delegate_to = None
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            if tc["name"] == "delegate_to_sub_agent":
                delegate_to = tc["args"].get("agent_name")
                break

    return {
        "messages": [response],
        "delegate_to": delegate_to,
    }


def route_after_orchestrator(state: ResearchState) -> str:
    """Conditional edge: decide where to go after the orchestrator responds."""
    messages = list(state.get("messages") or [])
    if not messages:
        return "end"
    last = messages[-1]

    if not (hasattr(last, "tool_calls") and last.tool_calls):
        return "end"

    # Delegation takes priority over regular tool calls
    for tc in last.tool_calls:
        if tc["name"] == "delegate_to_sub_agent":
            return tc["args"].get("agent_name", "end")

    return "tools"
