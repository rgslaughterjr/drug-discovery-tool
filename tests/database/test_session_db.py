"""Tests for ResearchSession CRUD operations."""

import pytest

from src.database.session_db import (
    create_research_session,
    delete_research_session,
    get_research_session,
    list_research_sessions,
    update_research_session,
)


AUTH_SID = "auth-session-test-001"


class TestCreateResearchSession:
    def test_returns_uuid_string(self, db_conn):
        rs_id = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")
        assert isinstance(rs_id, str)
        assert len(rs_id) == 36  # UUID4

    def test_default_name_untitled(self, db_conn):
        rs_id = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")
        row = get_research_session(db_conn, rs_id)
        assert row["name"] == "Untitled Research"

    def test_custom_name_stored(self, db_conn):
        rs_id = create_research_session(
            db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6", name="My Target"
        )
        row = get_research_session(db_conn, rs_id)
        assert row["name"] == "My Target"

    def test_provider_and_model_stored(self, db_conn):
        rs_id = create_research_session(db_conn, AUTH_SID, "openai", "gpt-4o")
        row = get_research_session(db_conn, rs_id)
        assert row["provider"] == "openai"
        assert row["model"] == "gpt-4o"


class TestGetResearchSession:
    def test_returns_none_for_unknown_id(self, db_conn):
        assert get_research_session(db_conn, "nonexistent-id") is None

    def test_returns_dict_with_expected_keys(self, db_conn):
        rs_id = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")
        row = get_research_session(db_conn, rs_id)
        for key in ("id", "auth_session_id", "name", "provider", "model", "pipeline_stage"):
            assert key in row

    def test_auth_session_id_matches(self, db_conn):
        rs_id = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")
        row = get_research_session(db_conn, rs_id)
        assert row["auth_session_id"] == AUTH_SID


class TestListResearchSessions:
    def test_returns_empty_list_for_unknown_auth(self, db_conn):
        results = list_research_sessions(db_conn, "nobody")
        assert results == []

    def test_lists_sessions_for_auth(self, db_conn):
        create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6", name="A")
        create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6", name="B")
        results = list_research_sessions(db_conn, AUTH_SID)
        assert len(results) == 2

    def test_does_not_leak_other_auth_sessions(self, db_conn):
        create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")
        create_research_session(db_conn, "other-auth-999", "openai", "gpt-4o")
        results = list_research_sessions(db_conn, AUTH_SID)
        assert len(results) == 1

    def test_ordered_by_last_active_desc(self, db_conn):
        id1 = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6", name="Old")
        id2 = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6", name="New")
        # Touch the first session to make it most-recently-active
        update_research_session(db_conn, id1, name="Old-updated")
        results = list_research_sessions(db_conn, AUTH_SID)
        assert results[0]["id"] == id1


class TestUpdateResearchSession:
    def test_updates_pipeline_stage(self, db_conn):
        rs_id = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")
        update_research_session(db_conn, rs_id, pipeline_stage="controls")
        row = get_research_session(db_conn, rs_id)
        assert row["pipeline_stage"] == "controls"

    def test_updates_uniprot_and_pdb(self, db_conn):
        rs_id = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")
        update_research_session(db_conn, rs_id, uniprot_id="P0A749", pdb_id="4P8O")
        row = get_research_session(db_conn, rs_id)
        assert row["uniprot_id"] == "P0A749"
        assert row["pdb_id"] == "4P8O"

    def test_last_active_at_updated(self, db_conn):
        rs_id = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")
        before = get_research_session(db_conn, rs_id)["last_active_at"]
        update_research_session(db_conn, rs_id, name="touched")
        after = get_research_session(db_conn, rs_id)["last_active_at"]
        assert after >= before


class TestDeleteResearchSession:
    def test_delete_removes_row(self, db_conn):
        rs_id = create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")
        delete_research_session(db_conn, rs_id)
        assert get_research_session(db_conn, rs_id) is None

    def test_delete_nonexistent_is_noop(self, db_conn):
        delete_research_session(db_conn, "does-not-exist")  # should not raise
