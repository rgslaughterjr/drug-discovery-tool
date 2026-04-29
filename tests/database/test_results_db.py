"""Tests for WorkflowResult and VerifiedCompound CRUD operations."""

import json

import pytest

from src.database.results_db import (
    delete_results,
    get_verified_compounds,
    get_workflow_results,
    save_verified_compounds,
    save_workflow_result,
)
from src.database.session_db import create_research_session

AUTH_SID = "auth-results-test-001"

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

CLOROBIOCIN = {
    "compound_type": "positive_control",
    "name": "Clorobiocin",
    "chembl_id": "CHEMBL1211",
    "pubchem_cid": 3052799,
    "smiles": "COC1=CC(=CC2=C1C(=O)C(=CO2)C(=O)N)OC3CC(O)(CC(C)(C)O3)N4C=CC(=O)NC4=O",
    "mw": 697.1,
    "logp": 3.1,
    "hbd": 2,
    "hba": 11,
    "activity_value_nm": 18.0,
    "activity_type": "IC50",
    "is_pains": False,
    "rank": 2,
}


@pytest.fixture()
def rs_id(db_conn):
    return create_research_session(db_conn, AUTH_SID, "anthropic", "claude-sonnet-4-6")


@pytest.fixture()
def wr_id(db_conn, rs_id):
    return save_workflow_result(
        db_conn, rs_id,
        workflow_type="evaluate_target",
        result={"recommendation": "GO", "uniprot_id": "P0A749"},
        model_used="claude-sonnet-4-6",
        is_verified=True,
    )


class TestSaveWorkflowResult:
    def test_returns_uuid_string(self, db_conn, rs_id):
        wr_id = save_workflow_result(
            db_conn, rs_id, "evaluate_target",
            {"recommendation": "GO"}, "claude-sonnet-4-6",
        )
        assert isinstance(wr_id, str)
        assert len(wr_id) == 36

    def test_result_persisted_as_json(self, db_conn, rs_id):
        payload = {"recommendation": "GO", "score": 5}
        wr_id = save_workflow_result(
            db_conn, rs_id, "evaluate_target", payload, "claude-sonnet-4-6",
        )
        rows = get_workflow_results(db_conn, rs_id)
        assert len(rows) == 1
        stored = json.loads(rows[0]["result_json"])
        assert stored["recommendation"] == "GO"

    def test_tool_calls_audit_log_stored(self, db_conn, rs_id):
        tool_calls = [{"tool": "uniprot_search", "input": {"query": "GyrB"}}]
        wr_id = save_workflow_result(
            db_conn, rs_id, "evaluate_target",
            {}, "claude-sonnet-4-6", tool_calls=tool_calls,
        )
        rows = get_workflow_results(db_conn, rs_id)
        stored_calls = json.loads(rows[0]["tool_calls_json"])
        assert stored_calls[0]["tool"] == "uniprot_search"

    def test_is_verified_flag(self, db_conn, rs_id):
        wr_id = save_workflow_result(
            db_conn, rs_id, "get_controls", {}, "claude-sonnet-4-6", is_verified=True,
        )
        rows = get_workflow_results(db_conn, rs_id, workflow_type="get_controls")
        assert rows[0]["is_verified"] is True


class TestGetWorkflowResults:
    def test_filter_by_workflow_type(self, db_conn, rs_id):
        save_workflow_result(db_conn, rs_id, "evaluate_target", {}, "claude-sonnet-4-6")
        save_workflow_result(db_conn, rs_id, "get_controls", {}, "claude-sonnet-4-6")
        rows = get_workflow_results(db_conn, rs_id, workflow_type="evaluate_target")
        assert len(rows) == 1
        assert rows[0]["workflow_type"] == "evaluate_target"

    def test_returns_all_when_type_not_filtered(self, db_conn, rs_id):
        save_workflow_result(db_conn, rs_id, "evaluate_target", {}, "claude-sonnet-4-6")
        save_workflow_result(db_conn, rs_id, "get_controls", {}, "claude-sonnet-4-6")
        rows = get_workflow_results(db_conn, rs_id)
        assert len(rows) == 2

    def test_empty_for_unknown_session(self, db_conn):
        rows = get_workflow_results(db_conn, "ghost-session")
        assert rows == []


class TestSaveVerifiedCompounds:
    def test_bulk_insert(self, db_conn, rs_id, wr_id):
        save_verified_compounds(db_conn, wr_id, rs_id, [NOVOBIOCIN, CLOROBIOCIN])
        compounds = get_verified_compounds(db_conn, rs_id)
        assert len(compounds) == 2

    def test_pubchem_cid_stored(self, db_conn, rs_id, wr_id):
        save_verified_compounds(db_conn, wr_id, rs_id, [NOVOBIOCIN])
        compounds = get_verified_compounds(db_conn, rs_id)
        assert compounds[0]["pubchem_cid"] == 54676895

    def test_pains_alerts_joined_as_string(self, db_conn, rs_id, wr_id):
        compound = {**NOVOBIOCIN, "is_pains": True, "pains_alerts": ["rule_a", "rule_b"]}
        save_verified_compounds(db_conn, wr_id, rs_id, [compound])
        compounds = get_verified_compounds(db_conn, rs_id)
        assert compounds[0]["pains_alerts"] == "rule_a,rule_b"

    def test_empty_list_is_noop(self, db_conn, rs_id, wr_id):
        save_verified_compounds(db_conn, wr_id, rs_id, [])
        compounds = get_verified_compounds(db_conn, rs_id)
        assert len(compounds) == 0


class TestGetVerifiedCompounds:
    def test_filter_by_compound_type(self, db_conn, rs_id, wr_id):
        save_verified_compounds(db_conn, wr_id, rs_id, [NOVOBIOCIN, CLOROBIOCIN])
        decoy = {**NOVOBIOCIN, "compound_type": "negative_control", "name": "Decoy1", "rank": 3}
        save_verified_compounds(db_conn, wr_id, rs_id, [decoy])
        pos = get_verified_compounds(db_conn, rs_id, compound_type="positive_control")
        assert len(pos) == 2
        neg = get_verified_compounds(db_conn, rs_id, compound_type="negative_control")
        assert len(neg) == 1

    def test_ordered_by_rank_asc(self, db_conn, rs_id, wr_id):
        save_verified_compounds(db_conn, wr_id, rs_id, [CLOROBIOCIN, NOVOBIOCIN])
        compounds = get_verified_compounds(db_conn, rs_id)
        assert compounds[0]["rank"] == 1   # Novobiocin
        assert compounds[1]["rank"] == 2   # Clorobiocin


class TestDeleteResults:
    def test_cascade_deletes_compounds(self, db_conn, rs_id, wr_id):
        save_verified_compounds(db_conn, wr_id, rs_id, [NOVOBIOCIN])
        delete_results(db_conn, rs_id)
        assert get_workflow_results(db_conn, rs_id) == []

    def test_delete_nonexistent_is_noop(self, db_conn):
        delete_results(db_conn, "ghost-session")  # should not raise
