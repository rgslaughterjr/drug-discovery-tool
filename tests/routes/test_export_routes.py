"""Tests for /api/export/{id}/compounds.csv and /results.json endpoints."""

import pytest
from unittest.mock import patch
from starlette.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from src.database.models import init_db
from src.database.session_db import create_research_session
from src.database.results_db import save_workflow_result, save_verified_compounds
from src.session_manager import SessionStore


def _make_memory_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    return engine

NOVOBIOCIN = {
    "compound_type": "positive_control",
    "name": "Novobiocin",
    "chembl_id": "CHEMBL1107",
    "pubchem_cid": 54676895,
    "smiles": "CC1(C)C(O)CC(O1)OC2=CC(=CC3=C2C(=O)C(=CO3)C(=O)N)OC",
    "canonical_smiles": "CC1(C)C(O)CC(O1)OC2=CC(=CC3=C2C(=O)C(=CO3)C(=O)N)OC",
    "mw": 612.6,
    "logp": 2.8,
    "tpsa": 145.8,
    "hbd": 3,
    "hba": 10,
    "activity_value_nm": 33.0,
    "activity_type": "IC50",
    "is_pains": False,
    "rank": 1,
    "notes": "Clinical aminocoumarin antibiotic",
}


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
def seeded(isolated_engine, sid):
    """Returns (rs_id, wr_id) with one Novobiocin compound inserted."""
    with isolated_engine.connect() as conn:
        rs_id = create_research_session(conn, sid, "anthropic", "claude-sonnet-4-6", name="GyrB")
        wr_id = save_workflow_result(
            conn, rs_id, "get_controls",
            {"recommendation": "GO"}, "claude-sonnet-4-6", is_verified=True,
        )
        save_verified_compounds(conn, wr_id, rs_id, [NOVOBIOCIN])
    return rs_id, wr_id


@pytest.fixture()
def export_client(isolated_engine, store, sid):
    from src.main import app
    with patch("src.routes.agent.session_store", store), \
         patch("src.routes.export.session_store", store):
        with TestClient(app) as c:
            app.state.db_engine = isolated_engine
            c.headers["X-Session-ID"] = sid
            yield c


# ---------------------------------------------------------------------------
# GET /api/export/{id}/compounds.csv
# ---------------------------------------------------------------------------

class TestExportCompoundsCsv:
    def test_401_without_session(self, isolated_engine, store):
        from src.main import app
        with patch("src.routes.agent.session_store", store), \
             patch("src.routes.export.session_store", store):
            with TestClient(app) as c:
                app.state.db_engine = isolated_engine
                resp = c.get("/api/export/any-id/compounds.csv")
                assert resp.status_code == 401

    def test_404_for_unknown_research_session(self, export_client):
        resp = export_client.get("/api/export/no-such-session/compounds.csv")
        assert resp.status_code == 404

    def test_404_when_no_compounds(self, export_client, isolated_engine, sid):
        with isolated_engine.connect() as conn:
            rs_id = create_research_session(conn, sid, "anthropic", "claude-sonnet-4-6")
        resp = export_client.get(f"/api/export/{rs_id}/compounds.csv")
        assert resp.status_code == 404

    def test_csv_content_type(self, export_client, seeded):
        rs_id, _ = seeded
        resp = export_client.get(f"/api/export/{rs_id}/compounds.csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

    def test_csv_contains_header_row(self, export_client, seeded):
        rs_id, _ = seeded
        resp = export_client.get(f"/api/export/{rs_id}/compounds.csv")
        assert resp.status_code == 200
        first_line = resp.text.splitlines()[0]
        assert "name" in first_line
        assert "smiles" in first_line
        assert "pubchem_cid" in first_line

    def test_csv_contains_novobiocin_row(self, export_client, seeded):
        rs_id, _ = seeded
        resp = export_client.get(f"/api/export/{rs_id}/compounds.csv")
        assert "Novobiocin" in resp.text
        assert "54676895" in resp.text

    def test_content_disposition_attachment(self, export_client, seeded):
        rs_id, _ = seeded
        resp = export_client.get(f"/api/export/{rs_id}/compounds.csv")
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert ".csv" in cd

    def test_cannot_export_other_auth_session(self, isolated_engine, store):
        """Auth B cannot export compounds belonging to Auth A."""
        from src.main import app

        sid_a = store.create("anthropic", "sk-ant-a", "claude-sonnet-4-6")
        sid_b = store.create("anthropic", "sk-ant-b", "claude-sonnet-4-6")

        with isolated_engine.connect() as conn:
            rs_id = create_research_session(conn, sid_a, "anthropic", "claude-sonnet-4-6")
            wr_id = save_workflow_result(conn, rs_id, "get_controls", {}, "claude-sonnet-4-6")
            save_verified_compounds(conn, wr_id, rs_id, [NOVOBIOCIN])

        with patch("src.routes.agent.session_store", store), \
             patch("src.routes.export.session_store", store):
            with TestClient(app) as c:
                app.state.db_engine = isolated_engine
                c.headers["X-Session-ID"] = sid_b
                resp = c.get(f"/api/export/{rs_id}/compounds.csv")
                assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/export/{id}/results.json
# ---------------------------------------------------------------------------

class TestExportResultsJson:
    def test_401_without_session(self, isolated_engine, store):
        from src.main import app
        with patch("src.routes.agent.session_store", store), \
             patch("src.routes.export.session_store", store):
            with TestClient(app) as c:
                app.state.db_engine = isolated_engine
                resp = c.get("/api/export/any-id/results.json")
                assert resp.status_code == 401

    def test_404_for_unknown_session(self, export_client):
        resp = export_client.get("/api/export/ghost/results.json")
        assert resp.status_code == 404

    def test_json_structure(self, export_client, seeded):
        rs_id, _ = seeded
        resp = export_client.get(f"/api/export/{rs_id}/results.json")
        assert resp.status_code == 200
        body = resp.json()
        assert "research_session" in body
        assert "workflow_results" in body
        assert "verified_compounds" in body

    def test_compounds_included_in_json(self, export_client, seeded):
        rs_id, _ = seeded
        resp = export_client.get(f"/api/export/{rs_id}/results.json")
        body = resp.json()
        names = [c["name"] for c in body["verified_compounds"]]
        assert "Novobiocin" in names

    def test_tool_calls_omitted_from_export(self, export_client, seeded):
        """Verbose audit log must not appear in the user-facing JSON export."""
        rs_id, _ = seeded
        resp = export_client.get(f"/api/export/{rs_id}/results.json")
        body = resp.json()
        for wr in body["workflow_results"]:
            assert "tool_calls_json" not in wr
