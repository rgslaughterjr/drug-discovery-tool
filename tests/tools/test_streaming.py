"""Tests for SSEEvent dataclass and factory functions."""

import json

import pytest

from src.agent.streaming import (
    SSEEvent,
    done_event,
    error_event,
    structured_result_event,
    sub_agent_done_event,
    sub_agent_start_event,
    text_delta_event,
    thinking_event,
    tool_result_event,
    _summarize_tool_result,
)


# ---------------------------------------------------------------------------
# SSEEvent serialisation
# ---------------------------------------------------------------------------

class TestSSEEvent:
    def test_to_json_omits_none_fields(self):
        event = SSEEvent(type="thinking", tool="chembl_bioactivity", status="calling")
        payload = json.loads(event.to_json())
        assert payload["type"] == "thinking"
        assert payload["tool"] == "chembl_bioactivity"
        assert "content" not in payload
        assert "agent" not in payload

    def test_to_sse_line_format(self):
        event = SSEEvent(type="done", research_session_id="abc-123")
        line = event.to_sse_line()
        assert line.startswith("data: ")
        assert line.endswith("\n\n")
        inner = json.loads(line[len("data: "):].strip())
        assert inner["type"] == "done"
        assert inner["research_session_id"] == "abc-123"

    def test_to_json_roundtrip(self):
        event = SSEEvent(
            type="structured_result",
            result_type="compound_table",
            data={"rows": [{"name": "Novobiocin", "cid": 54676895}]},
        )
        raw = event.to_json()
        parsed = json.loads(raw)
        assert parsed["data"]["rows"][0]["name"] == "Novobiocin"


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

class TestFactoryFunctions:
    def test_thinking_event(self):
        e = thinking_event("uniprot_search")
        assert e.type == "thinking"
        assert e.tool == "uniprot_search"
        assert e.status == "calling"

    def test_tool_result_event_includes_duration(self):
        e = tool_result_event("validate_smiles", {"valid": True, "mw": 612.6}, duration_ms=42)
        assert e.type == "tool_result"
        assert e.duration_ms == 42
        assert e.tool == "validate_smiles"

    def test_text_delta_event(self):
        e = text_delta_event("Found 14 inhibitors")
        assert e.type == "text_delta"
        assert e.content == "Found 14 inhibitors"

    def test_sub_agent_start_event(self):
        e = sub_agent_start_event("controls_generator")
        assert e.type == "sub_agent_start"
        assert e.agent == "controls_generator"
        assert e.status == "running"

    def test_sub_agent_done_event(self):
        e = sub_agent_done_event("controls_generator", "compound_table", {"count": 5})
        assert e.type == "sub_agent_done"
        assert e.result_type == "compound_table"

    def test_structured_result_event_list_wraps_in_rows(self):
        compounds = [{"name": "Novobiocin"}, {"name": "Clorobiocin"}]
        e = structured_result_event("compound_table", compounds)
        assert e.data["rows"] == compounds

    def test_structured_result_event_dict_passes_through(self):
        data = {"recommendation": "GO", "uniprot_id": "P0A749"}
        e = structured_result_event("evaluation", data)
        assert e.data["recommendation"] == "GO"

    def test_done_event(self):
        e = done_event("rs-999", usage={"input_tokens": 100, "output_tokens": 50})
        assert e.type == "done"
        assert e.research_session_id == "rs-999"
        assert e.usage["input_tokens"] == 100

    def test_error_event(self):
        e = error_event("ChEMBL API timeout")
        assert e.type == "error"
        assert e.message == "ChEMBL API timeout"


# ---------------------------------------------------------------------------
# _summarize_tool_result token efficiency
# ---------------------------------------------------------------------------

class TestSummarizeToolResult:
    def test_uniprot_search_summary(self):
        data = {
            "found": True,
            "entries": [{"uniprot_id": "P0A749", "gene": "gyrB"}],
        }
        s = _summarize_tool_result("uniprot_search", data)
        assert s["found"] is True
        assert s["count"] == 1
        assert s["top"]["uniprot_id"] == "P0A749"

    def test_chembl_bioactivity_summary(self):
        data = {
            "found": True,
            "compounds": [
                {"name": "Novobiocin", "activity_nm": 33.0},
                {"name": "Clorobiocin", "activity_nm": 18.0},
            ],
        }
        s = _summarize_tool_result("chembl_bioactivity", data)
        assert s["best_nm"] == 18.0
        assert s["count"] == 2

    def test_validate_smiles_summary(self):
        data = {"valid": True, "mw": 612.6, "ro5_violations": 1}
        s = _summarize_tool_result("validate_smiles", data)
        assert s["valid"] is True
        assert s["mw"] == 612.6

    def test_screen_pains_summary(self):
        data = {
            "results": [
                {"smiles": "C", "is_pains": False},
                {"smiles": "CC", "is_pains": True},
            ],
            "pains_count": 1,
        }
        s = _summarize_tool_result("screen_pains", data)
        assert s["screened"] == 2
        assert s["pains_count"] == 1

    def test_non_dict_input_returns_empty(self):
        s = _summarize_tool_result("any_tool", "not a dict")
        assert s == {}

    def test_unknown_tool_returns_first_four_keys(self):
        data = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
        s = _summarize_tool_result("unknown_tool", data)
        assert len(s) == 4
