"""Tests for /api/agent/research-sessions CRUD endpoints."""

import pytest
from unittest.mock import patch
from starlette.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from src.database.models import init_db, metadata
from src.session_manager import SessionStore


def _make_memory_engine():
    """In-memory SQLite engine with StaticPool so all connections share one DB."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    return engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(isolated_engine, store, sid=None):
    """Return a TestClient with the test engine and store injected."""
    from src.main import app

    with patch("src.routes.agent.session_store", store), \
         patch("src.routes.export.session_store", store):
        client = TestClient(app, raise_server_exceptions=True)
        client.__enter__()
        # Override db_engine AFTER startup event (which sets the real one)
        app.state.db_engine = isolated_engine
        if sid:
            client.headers["X-Session-ID"] = sid
        return client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_engine():
    engine = _make_memory_engine()
    yield engine
    engine.dispose()


@pytest.fixture()
def store():
    return SessionStore(ttl_minutes=30)


@pytest.fixture()
def sid(store):
    return store.create("anthropic", "sk-ant-test", "claude-sonnet-4-6")


@pytest.fixture()
def client(isolated_engine, store, sid):
    from src.main import app
    with patch("src.routes.agent.session_store", store), \
         patch("src.routes.export.session_store", store):
        with TestClient(app=app, raise_server_exceptions=True) as c:
            app.state.db_engine = isolated_engine
            c.headers["X-Session-ID"] = sid
            yield c


# ---------------------------------------------------------------------------
# POST /api/agent/research-sessions
# ---------------------------------------------------------------------------

class TestCreateResearchSession:
    def test_creates_session_returns_id(self, client):
        resp = client.post("/api/agent/research-sessions", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert "research_session_id" in body
        assert body["status"] == "created"

    def test_creates_named_session(self, client):
        resp = client.post("/api/agent/research-sessions", json={"name": "GyrB study"})
        assert resp.status_code == 200

    def test_requires_valid_auth_session(self, client):
        resp = client.post(
            "/api/agent/research-sessions", json={},
            headers={"X-Session-ID": "bogus-session-id"},
        )
        assert resp.status_code == 401

    def test_missing_session_header_is_401(self, isolated_engine, store):
        from src.main import app
        with patch("src.routes.agent.session_store", store), \
             patch("src.routes.export.session_store", store):
            with TestClient(app) as c:
                app.state.db_engine = isolated_engine
                resp = c.post("/api/agent/research-sessions", json={})
                assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/agent/research-sessions
# ---------------------------------------------------------------------------

class TestListResearchSessions:
    def test_empty_list_for_new_auth(self, client):
        resp = client.get("/api/agent/research-sessions")
        assert resp.status_code == 200
        assert resp.json()["sessions"] == []

    def test_lists_created_sessions(self, client):
        client.post("/api/agent/research-sessions", json={"name": "Alpha"})
        client.post("/api/agent/research-sessions", json={"name": "Beta"})
        resp = client.get("/api/agent/research-sessions")
        assert resp.status_code == 200
        assert len(resp.json()["sessions"]) == 2

    def test_requires_valid_session(self, client):
        resp = client.get(
            "/api/agent/research-sessions",
            headers={"X-Session-ID": "expired-id"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/agent/research-sessions/{id}
# ---------------------------------------------------------------------------

class TestGetResearchSession:
    def test_get_existing_session(self, client):
        create_resp = client.post("/api/agent/research-sessions", json={"name": "Test"})
        rs_id = create_resp.json()["research_session_id"]

        resp = client.get(f"/api/agent/research-sessions/{rs_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "session" in body
        assert "conversation_length" in body
        assert body["conversation_length"] == 0

    def test_404_for_unknown_id(self, client):
        resp = client.get("/api/agent/research-sessions/does-not-exist")
        assert resp.status_code == 404

    def test_cannot_access_other_auth_session(self, isolated_engine, store):
        """Session created by auth A should not be visible to auth B."""
        from src.main import app

        sid_a = store.create("anthropic", "sk-ant-a", "claude-sonnet-4-6")
        sid_b = store.create("anthropic", "sk-ant-b", "claude-sonnet-4-6")

        with patch("src.routes.agent.session_store", store), \
             patch("src.routes.export.session_store", store):
            with TestClient(app) as c:
                app.state.db_engine = isolated_engine
                c.headers["X-Session-ID"] = sid_a
                rs_id = c.post("/api/agent/research-sessions", json={}).json()["research_session_id"]

                c.headers["X-Session-ID"] = sid_b
                resp = c.get(f"/api/agent/research-sessions/{rs_id}")
                assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/agent/research-sessions/{id}
# ---------------------------------------------------------------------------

class TestDeleteResearchSession:
    def test_delete_returns_status(self, client):
        create_resp = client.post("/api/agent/research-sessions", json={})
        rs_id = create_resp.json()["research_session_id"]

        resp = client.delete(f"/api/agent/research-sessions/{rs_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

    def test_deleted_session_is_gone(self, client):
        create_resp = client.post("/api/agent/research-sessions", json={})
        rs_id = create_resp.json()["research_session_id"]

        client.delete(f"/api/agent/research-sessions/{rs_id}")
        resp = client.get(f"/api/agent/research-sessions/{rs_id}")
        assert resp.status_code == 404

    def test_delete_unknown_id_is_404(self, client):
        resp = client.delete("/api/agent/research-sessions/ghost-id")
        assert resp.status_code == 404

    def test_cannot_delete_other_auth_session(self, isolated_engine, store):
        from src.main import app

        sid_a = store.create("anthropic", "sk-ant-a", "claude-sonnet-4-6")
        sid_b = store.create("anthropic", "sk-ant-b", "claude-sonnet-4-6")

        with patch("src.routes.agent.session_store", store), \
             patch("src.routes.export.session_store", store):
            with TestClient(app) as c:
                app.state.db_engine = isolated_engine
                c.headers["X-Session-ID"] = sid_a
                rs_id = c.post("/api/agent/research-sessions", json={}).json()["research_session_id"]

                c.headers["X-Session-ID"] = sid_b
                resp = c.delete(f"/api/agent/research-sessions/{rs_id}")
                assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/agent/chat — non-Anthropic provider rejection
# ---------------------------------------------------------------------------

class TestAgentChatProviderCheck:
    def test_openai_provider_rejected_with_400(self, isolated_engine, store):
        from src.main import app

        openai_sid = store.create("openai", "sk-openai-test", "gpt-4o")
        with patch("src.routes.agent.session_store", store), \
             patch("src.routes.export.session_store", store):
            with TestClient(app) as c:
                app.state.db_engine = isolated_engine
                c.headers["X-Session-ID"] = openai_sid
                resp = c.post("/api/agent/chat", json={"message": "Evaluate GyrB"})
                assert resp.status_code == 400
                detail = resp.json()["detail"].lower()
                assert "classic" in detail or "anthropic" in detail
