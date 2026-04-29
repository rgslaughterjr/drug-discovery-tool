"""Shared pytest fixtures for all backend tests."""

import pytest
from sqlalchemy.engine import Connection

from src.database.models import create_engine_from_path, init_db
from src.database.session_db import create_research_session
from src.session_manager import SessionStore


# ---------------------------------------------------------------------------
# In-memory SQLite engine (scoped per test function — full isolation)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_engine():
    """In-memory SQLite engine with schema initialised."""
    engine = create_engine_from_path(":memory:")
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_conn(db_engine):
    """Open connection from the in-memory engine."""
    with db_engine.connect() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Auth session store (fresh per test)
# ---------------------------------------------------------------------------

@pytest.fixture()
def session_store():
    """Isolated SessionStore — does NOT share state with the global _store."""
    return SessionStore(ttl_minutes=30)


@pytest.fixture()
def auth_session_id(session_store):
    """A valid auth session already in the store."""
    sid = session_store.create(
        provider="anthropic",
        api_key="sk-ant-test-key",
        model="claude-sonnet-4-6",
    )
    return sid


# ---------------------------------------------------------------------------
# Pre-seeded research session
# ---------------------------------------------------------------------------

@pytest.fixture()
def research_session_id(db_conn, auth_session_id):
    """A research session row already inserted in the DB."""
    return create_research_session(
        db_conn,
        auth_session_id=auth_session_id,
        provider="anthropic",
        model="claude-sonnet-4-6",
        name="Test: S. aureus GyrB",
    )


# ---------------------------------------------------------------------------
# FastAPI TestClient with wired-up state
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_app(db_engine, session_store):
    """
    FastAPI app with in-memory DB engine and isolated session store injected.
    Uses monkeypatching so routes see the test store, not the global one.
    """
    from src.main import app
    import src.routes.agent as agent_routes
    import src.routes.export as export_routes

    # Point both route modules at the test session store
    agent_routes._store_override = session_store
    export_routes._store_override = session_store

    app.state.db_engine = db_engine
    return app


@pytest.fixture()
def client(test_app, session_store, auth_session_id):
    """
    Synchronous TestClient with X-Session-ID header pre-set.
    Also patches the session_store used by routes.
    """
    from unittest.mock import patch
    from httpx import Client, ASGITransport

    with patch("src.routes.agent._store", session_store), \
         patch("src.routes.export._store", session_store):
        transport = ASGITransport(app=test_app)
        with Client(transport=transport, base_url="http://test") as c:
            c.headers["X-Session-ID"] = auth_session_id
            yield c
