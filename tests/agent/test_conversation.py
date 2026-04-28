"""Tests for ConversationHistory load/save/compress logic."""

import pytest

from src.agent.conversation import ConversationHistory
from src.database.conversation_db import count_turns
from src.database.session_db import create_research_session

AUTH_SID = "auth-conv-history-001"


@pytest.fixture()
def rs_id(db_conn):
    return create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")


@pytest.fixture()
def history(db_conn, rs_id):
    return ConversationHistory(rs_id, db_conn)


class TestConversationHistoryLoad:
    def test_load_empty_session(self, history):
        messages = history.load()
        assert messages == []

    def test_messages_property_triggers_load(self, history):
        assert history.messages == []

    def test_loaded_flag_prevents_double_load(self, db_conn, rs_id):
        h = ConversationHistory(rs_id, db_conn)
        h.load()
        assert h._loaded is True
        h.load()  # second call should be no-op (covered by _loaded guard)
        assert h._loaded is True


class TestConversationHistoryAdd:
    def test_add_user_turn(self, history, db_conn, rs_id):
        history.add_user_turn("Evaluate GyrB as a target")
        assert len(history.messages) == 1
        assert history.messages[0]["role"] == "user"
        assert history.messages[0]["content"][0]["text"] == "Evaluate GyrB as a target"
        assert count_turns(db_conn, rs_id) == 1

    def test_add_assistant_turn(self, history, db_conn, rs_id):
        history.add_user_turn("Question")
        history.add_assistant_turn([{"type": "text", "text": "Answer"}])
        assert len(history.messages) == 2
        assert history.messages[1]["role"] == "assistant"
        assert count_turns(db_conn, rs_id) == 2

    def test_add_tool_result_turn(self, history, db_conn, rs_id):
        history.add_tool_result_turn([
            {"type": "tool_result", "tool_use_id": "tu_1", "content": "P0A749"}
        ])
        assert history.messages[0]["role"] == "user"
        assert count_turns(db_conn, rs_id) == 1

    def test_turn_indices_sequential(self, history):
        history.add_user_turn("Q1")
        history.add_assistant_turn([{"type": "text", "text": "A1"}])
        history.add_user_turn("Q2")
        assert len(history.messages) == 3


class TestConversationHistoryCompress:
    def _setup_tool_exchange(self, history):
        """Build a realistic 4-message tool exchange."""
        history.add_user_turn("Evaluate Staphylococcus aureus GyrB as a drug target")
        history.add_assistant_turn([
            {"type": "text", "text": "I'll look that up."},
            {"type": "tool_use", "id": "tu_1", "name": "uniprot_search",
             "input": {"query": "GyrB Staphylococcus aureus"}},
        ])
        history.add_tool_result_turn([
            {"type": "tool_result", "tool_use_id": "tu_1",
             "content": [{"type": "text", "text": '{"entries": [{"uniprot_id": "P0A749"}]}'}]},
        ])
        history.add_assistant_turn([
            {"type": "text", "text": "GO. UniProt P0A749; best structure 4P8O."},
        ])

    def test_compress_removes_tool_use_from_history(self, history, db_conn, rs_id):
        self._setup_tool_exchange(history)
        assert len(history.messages) == 4

        history.compress_last_workflow({
            "workflow_type": "evaluate_target",
            "organism": "Staphylococcus aureus",
            "protein": "GyrB",
            "key_findings": "GO. UniProt P0A749; best structure 4P8O at 1.95 Å.",
        })

        # Tool_use turn + following tool_result turn should both be collapsed
        has_tool_use = any(
            isinstance(m["content"], list) and
            any(b.get("type") == "tool_use" for b in m["content"] if isinstance(b, dict))
            for m in history.messages
        )
        assert not has_tool_use

    def test_compress_inserts_summary_block(self, history):
        self._setup_tool_exchange(history)
        history.compress_last_workflow({
            "workflow_type": "evaluate_target",
            "organism": "Staphylococcus aureus",
            "protein": "GyrB",
            "key_findings": "GO.",
        })
        found_summary = any(
            isinstance(m["content"], list) and
            any("[WORKFLOW COMPLETE" in b.get("text", "") for b in m["content"] if isinstance(b, dict))
            for m in history.messages
        )
        assert found_summary

    def test_compress_persists_to_sqlite(self, history, db_conn, rs_id):
        self._setup_tool_exchange(history)
        before = count_turns(db_conn, rs_id)

        history.compress_last_workflow({
            "workflow_type": "evaluate_target",
            "organism": "S. aureus",
            "protein": "GyrB",
            "key_findings": "GO.",
        })

        after = count_turns(db_conn, rs_id)
        # Compression should produce fewer stored turns
        assert after < before

    def test_compress_noop_when_no_tool_use(self, history):
        history.add_user_turn("What does TPSA mean?")
        history.add_assistant_turn([{"type": "text", "text": "TPSA is..."}])
        before_len = len(history.messages)

        history.compress_last_workflow({
            "workflow_type": "evaluate_target",
            "organism": "",
            "protein": "",
            "key_findings": "",
        })

        # No tool_use → nothing compressed → length unchanged
        assert len(history.messages) == before_len


class TestTokenEstimate:
    def test_empty_history_zero(self, history):
        assert history.token_estimate() == 0

    def test_increases_with_turns(self, history):
        history.add_user_turn("Short question")
        t1 = history.token_estimate()
        history.add_assistant_turn([{"type": "text", "text": "A longer answer " * 20}])
        t2 = history.token_estimate()
        assert t2 > t1

    def test_decreases_after_compression(self, history):
        history.add_user_turn("Evaluate GyrB")
        history.add_assistant_turn([
            {"type": "tool_use", "id": "tu_1", "name": "uniprot_search", "input": {}},
        ])
        history.add_tool_result_turn([
            {"type": "tool_result", "tool_use_id": "tu_1",
             "content": [{"type": "text", "text": "x" * 500}]},
        ])
        t_before = history.token_estimate()

        history.compress_last_workflow({
            "workflow_type": "evaluate_target",
            "organism": "S. aureus",
            "protein": "GyrB",
            "key_findings": "GO.",
        })
        t_after = history.token_estimate()
        assert t_after < t_before
