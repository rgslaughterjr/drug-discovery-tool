"""
Orchestrator node — Claude Sonnet as the reasoning brain.

Receives the full conversation, decides whether to:
  1. Call a domain tool directly (→ ToolNode)
  2. Delegate to a Nemotron sub-agent  (→ sub-agent node)
  3. Answer directly or ask for clarification (→ END)

Prompt-caching strategy (Anthropic — ~90% discount on cached tokens):
  Cache breakpoint 1: system message text block (~300 tokens)
  Cache breakpoint 2: last tool in the tools array (~2,400 tokens total for 16 tools)
  Combined cached prefix ≈ 2,700 tokens → saves ~2,430 tokens every orchestrator call.
  Tool schemas and system block are computed once at module import and reused.
"""

from __future__ import annotations

import os
from typing import Literal, Optional

from langchain_anthropic import ChatAnthropic
from langchain_anthropic.chat_models import convert_to_anthropic_tool
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool

from src.agent import context as _ctx
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

# Cache breakpoint 1: system block — marked so Anthropic caches everything up to here.
# Must be passed as a list of content dicts (not a plain string) for cache_control to work.
_SYSTEM_BLOCK = [
    {
        "type": "text",
        "text": _ORCHESTRATOR_SYSTEM,
        "cache_control": {"type": "ephemeral"},
    }
]

_MAX_ORCHESTRATOR_TURNS = 6
_MESSAGE_WINDOW = 20


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
    # Routing happens in the graph edge; this function is never called directly.
    return f"Delegating to {agent_name}: {task_description}"


ORCHESTRATOR_TOOLS = ALL_TOOLS + [delegate_to_sub_agent]

# Cache breakpoint 2: pre-format all tool schemas once; mark the last tool so the
# entire tools array is cached together with the system block.
# Total cached prefix ≈ system (~300 tok) + tools (~2,400 tok) = ~2,700 tok per call.
def _build_cached_tool_schemas(tools: list) -> list[dict]:
    schemas = [convert_to_anthropic_tool(t) for t in tools]
    if schemas:
        schemas[-1] = {**schemas[-1], "cache_control": {"type": "ephemeral"}}
    return schemas


_ORCHESTRATOR_TOOL_SCHEMAS: list[dict] = _build_cached_tool_schemas(ORCHESTRATOR_TOOLS)


def _build_llm(api_key: str, model: str):
    """Build the Sonnet LLM with pre-cached tool schemas."""
    llm = ChatAnthropic(
        model=model,
        api_key=api_key,
        max_tokens=4096,
        temperature=0,
    )
    # bind() with pre-formatted schemas (including cache_control on last tool)
    # is equivalent to bind_tools() but avoids re-formatting on every request.
    return llm.bind(tools=_ORCHESTRATOR_TOOL_SCHEMAS)


async def orchestrator_node(state: ResearchState) -> dict:
    """Invoke Sonnet with the full conversation; return state update."""
    api_key = _ctx.anthropic_key.get() or os.environ.get("ANTHROPIC_API_KEY", "")
    model = state.get("model") or os.getenv("ORCHESTRATOR_MODEL", "claude-sonnet-4-6")

    llm = _build_llm(api_key, model)

    # Trim conversation to the most recent N messages to bound context growth
    all_messages = list(state["messages"])
    windowed = all_messages[-_MESSAGE_WINDOW:] if len(all_messages) > _MESSAGE_WINDOW else all_messages

    # SystemMessage with list content → langchain-anthropic passes cache_control through
    messages = [SystemMessage(content=_SYSTEM_BLOCK)] + windowed
    response = await llm.ainvoke(messages)

    delegate_to = None
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            if tc["name"] == "delegate_to_sub_agent":
                delegate_to = tc["args"].get("agent_name")
                break

    current_turns = state.get("orchestrator_turns", 0)
    return {
        "messages": [response],
        "delegate_to": delegate_to,
        "orchestrator_turns": current_turns + 1,
    }


def route_after_orchestrator(state: ResearchState) -> str:
    """Conditional edge: decide where to go after the orchestrator responds."""
    if state.get("orchestrator_turns", 0) >= _MAX_ORCHESTRATOR_TURNS:
        return "end"

    messages = list(state.get("messages") or [])
    if not messages:
        return "end"
    last = messages[-1]

    if not (hasattr(last, "tool_calls") and last.tool_calls):
        return "end"

    for tc in last.tool_calls:
        if tc["name"] == "delegate_to_sub_agent":
            return tc["args"].get("agent_name", "end")

    return "tools"
