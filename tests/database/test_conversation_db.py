"""Tests for ConversationTurn CRUD operations."""

import json

import pytest

from src.database.conversation_db import (
    compress_turn,
    count_turns,
    delete_turns,
    load_turns,
    save_turn,
)
from src.database.session_db import create_research_session

AUTH_SID = "auth-conv-test-001"


@pytest.fixture()
def rs_id(db_conn):
    return create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")


class TestSaveTurn:
    def test_save_user_turn_returns_row_id(self, db_conn, rs_id):
        row_id = save_turn(db_conn, rs_id, 0, "user", [{"type": "text", "text": "Hello"}])
        assert isinstance(row_id, int)
        assert row_id > 0

    def test_save_assistant_turn(self, db_conn, rs_id):
        save_turn(db_conn, rs_id, 0, "user", [{"type": "text", "text": "Hi"}])
        row_id = save_turn(
            db_conn, rs_id, 1, "assistant",
            [{"type": "text", "text": "GO. UniProt P0A749"}],
        )
        assert row_id > 0

    def test_content_as_list_serialised(self, db_conn, rs_id):
        content = [{"type": "text", "text": "Evaluate GyrB"}]
        save_turn(db_conn, rs_id, 0, "user", content)
        messages = load_turns(db_conn, rs_id)
        assert messages[0]["content"] == content

    def test_content_as_pre_serialized_json_string(self, db_conn, rs_id):
        # save_turn's str branch is for callers that pass already-serialized JSON
        import json
        content = [{"type": "text", "text": "pre-serialized"}]
        save_turn(db_conn, rs_id, 0, "user", json.dumps(content))
        messages = load_turns(db_conn, rs_id)
        assert messages[0]["content"] == content


class TestLoadTurns:
    def test_empty_session_returns_empty_list(self, db_conn, rs_id):
        assert load_turns(db_conn, rs_id) == []

    def test_ordered_by_turn_index(self, db_conn, rs_id):
        save_turn(db_conn, rs_id, 1, "assistant", [{"type": "text", "text": "Reply"}])
        save_turn(db_conn, rs_id, 0, "user", [{"type": "text", "text": "Question"}])
        messages = load_turns(db_conn, rs_id)
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_does_not_leak_other_sessions(self, db_conn, rs_id):
        other_rs = create_research_session(db_conn, "other-auth", "anthropic", "claude-sonnet-4-6")
        save_turn(db_conn, rs_id, 0, "user", [{"type": "text", "text": "session A"}])
        save_turn(db_conn, other_rs, 0, "user", [{"type": "text", "text": "session B"}])
        messages = load_turns(db_conn, rs_id)
        assert len(messages) == 1
        assert messages[0]["content"][0]["text"] == "session A"

    def test_returns_anthropic_message_format(self, db_conn, rs_id):
        save_turn(db_conn, rs_id, 0, "user", [{"type": "text", "text": "Hi"}])
        messages = load_turns(db_conn, rs_id)
        assert "role" in messages[0]
        assert "content" in messages[0]


class TestCompressTurn:
    def test_compress_replaces_content(self, db_conn, rs_id):
        row_id = save_turn(
            db_conn, rs_id, 0, "assistant",
            [{"type": "tool_use", "id": "tu_1", "name": "uniprot_search", "input": {}}],
        )
        summary = [{"type": "text", "text": "[WORKFLOW COMPLETE: evaluate_target]\nGO."}]
        compress_turn(db_conn, row_id, summary)
        messages = load_turns(db_conn, rs_id)
        assert messages[0]["content"] == summary

    def test_compress_unknown_id_is_noop(self, db_conn, rs_id):
        # Should not raise even if turn_id doesn't exist
        compress_turn(db_conn, 999999, [{"type": "text", "text": "summary"}])


class TestCountTurns:
    def test_zero_for_new_session(self, db_conn, rs_id):
        assert count_turns(db_conn, rs_id) == 0

    def test_counts_all_turns(self, db_conn, rs_id):
        save_turn(db_conn, rs_id, 0, "user", [{"type": "text", "text": "A"}])
        save_turn(db_conn, rs_id, 1, "assistant", [{"type": "text", "text": "B"}])
        save_turn(db_conn, rs_id, 2, "user", [{"type": "text", "text": "C"}])
        assert count_turns(db_conn, rs_id) == 3


class TestDeleteTurns:
    def test_delete_removes_all_turns(self, db_conn, rs_id):
        save_turn(db_conn, rs_id, 0, "user", [{"type": "text", "text": "A"}])
        save_turn(db_conn, rs_id, 1, "assistant", [{"type": "text", "text": "B"}])
        delete_turns(db_conn, rs_id)
        assert count_turns(db_conn, rs_id) == 0

    def test_delete_nonexistent_session_is_noop(self, db_conn):
        delete_turns(db_conn, "ghost-session")  # should not raise
