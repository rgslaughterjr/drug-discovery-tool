"""
SSEEvent dataclass + LangGraph event translator.

Translates LangGraph astream_events() output into typed SSE JSON events
that the React frontend can consume.

SSE event types:
  thinking        — graph node started/done
  tool_call       — tool call lifecycle
  text_delta      — incremental LLM text
  sub_agent_start — Nemotron sub-agent delegation beginning
  sub_agent_done  — sub-agent returned a result
  structured_result — compound table or evaluation result
  done            — stream complete
  error           — recoverable or fatal error
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass
class SSEEvent:
    type: str
    # text streaming
    content: Optional[str] = None
    # node lifecycle
    node: Optional[str] = None
    # tool call lifecycle
    tool: Optional[str] = None
    status: Optional[str] = None
    duration_ms: Optional[int] = None
    data: Optional[Any] = None
    # sub-agent
    agent: Optional[str] = None
    # structured result
    result_type: Optional[str] = None
    # session bookkeeping
    research_session_id: Optional[str] = None
    usage: Optional[dict] = None
    # error
    message: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps({k: v for k, v in asdict(self).items() if v is not None})

    def to_sse_line(self) -> str:
        return f"data: {self.to_json()}\n\n"


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------

def thinking_event(tool: str) -> SSEEvent:
    return SSEEvent(type="thinking", tool=tool, status="calling")


def tool_result_event(tool: str, data: dict, duration_ms: int) -> SSEEvent:
    # Trim data to a short summary to avoid large SSE payloads
    summary = _summarize_tool_result(tool, data)
    return SSEEvent(type="tool_result", tool=tool, data=summary, duration_ms=duration_ms)


def text_delta_event(content: str) -> SSEEvent:
    return SSEEvent(type="text_delta", content=content)


def sub_agent_start_event(agent: str) -> SSEEvent:
    return SSEEvent(type="sub_agent_start", agent=agent, status="running")


def sub_agent_done_event(agent: str, result_type: str, data: dict) -> SSEEvent:
    return SSEEvent(type="sub_agent_done", agent=agent, result_type=result_type, data=data)


def structured_result_event(result_type: str, data: list | dict) -> SSEEvent:
    return SSEEvent(type="structured_result", result_type=result_type, data={"rows": data} if isinstance(data, list) else data)


def done_event(research_session_id: str, usage: dict | None = None) -> SSEEvent:
    return SSEEvent(type="done", research_session_id=research_session_id, usage=usage)


def error_event(message: str) -> SSEEvent:
    return SSEEvent(type="error", message=message)


# ---------------------------------------------------------------------------
# Helper: produce a token-efficient SSE summary of a tool result
# ---------------------------------------------------------------------------

def _summarize_tool_result(tool: str, data: dict) -> dict:
    """Return a short summary dict for display in the AgentThinking component."""
    if not isinstance(data, dict):
        return {}

    if tool == "uniprot_search":
        entries = data.get("entries", [])
        return {
            "found": data.get("found"),
            "top": entries[0] if entries else None,
            "count": len(entries),
        }
    if tool == "uniprot_entry_detail":
        return {
            "uniprot_id": data.get("uniprot_id"),
            "gene": data.get("gene_name"),
            "organism": data.get("organism"),
            "essential": bool(data.get("essentiality_phenotype")),
        }
    if tool in ("pdb_structure_search",):
        structs = data.get("structures", [])
        return {
            "found": data.get("found"),
            "count": len(structs),
            "best": structs[0] if structs else None,
        }
    if tool == "pdb_binding_site_info":
        return {
            "pdb_id": data.get("pdb_id"),
            "resolution": data.get("resolution"),
            "ligand_count": data.get("ligand_count", 0),
        }
    if tool == "chembl_target_search":
        targets = data.get("targets", [])
        return {
            "found": data.get("found"),
            "count": len(targets),
            "top": targets[0] if targets else None,
        }
    if tool == "chembl_bioactivity":
        compounds = data.get("compounds", [])
        return {
            "found": data.get("found"),
            "count": len(compounds),
            "best_nm": min((c.get("activity_nm") or 9999 for c in compounds), default=None),
        }
    if tool in ("pubchem_compound_lookup",):
        return {
            "found": data.get("found"),
            "cid": data.get("cid"),
            "smiles_preview": (data.get("smiles") or "")[:40],
        }
    if tool == "validate_smiles":
        return {
            "valid": data.get("valid"),
            "mw": data.get("mw"),
            "ro5": data.get("ro5_violations"),
        }
    if tool == "screen_pains":
        results = data.get("results", [])
        return {
            "screened": len(results),
            "pains_count": data.get("pains_count", 0),
        }
    # Default: just return top-level keys, truncated
    return {k: v for k, v in list(data.items())[:4]}


# ---------------------------------------------------------------------------
# LangGraph astream_events() → SSE translation
# ---------------------------------------------------------------------------

_THINKING_NODES = {
    "orchestrator",
    "target_evaluator",
    "controls_generator",
    "screening_designer",
    "hits_analyzer",
    "synthesizer",
}


async def langgraph_events_to_sse(event_stream, research_session_id: str):
    """Consume a LangGraph astream_events() stream and yield SSE line strings."""
    tool_start_times: dict[str, float] = {}

    async for event in event_stream:
        kind = event.get("event", "")
        name = event.get("name", "")
        data = event.get("data", {})

        if kind == "on_chain_start" and name in _THINKING_NODES:
            yield SSEEvent(type="thinking", node=name, status="started").to_sse_line()

        elif kind == "on_chain_end" and name in _THINKING_NODES:
            yield SSEEvent(type="thinking", node=name, status="done").to_sse_line()

        elif kind == "on_tool_start":
            tool_start_times[name] = time.time()
            yield SSEEvent(type="tool_call", tool=name, status="calling").to_sse_line()

        elif kind == "on_tool_end":
            elapsed = int((time.time() - tool_start_times.pop(name, time.time())) * 1000)
            yield SSEEvent(type="tool_call", tool=name, status="done", duration_ms=elapsed).to_sse_line()

        elif kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk and hasattr(chunk, "content") and isinstance(chunk.content, str) and chunk.content:
                yield text_delta_event(chunk.content).to_sse_line()

    yield done_event(research_session_id).to_sse_line()
