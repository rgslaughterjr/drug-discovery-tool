"""
Seed the SQLite database with one pre-built research session (S. aureus GyrB)
so the UI is not empty on first launch.

Usage (from repo root):
  python dev/seed_test_data.py
Or inside Docker:
  docker compose -f dev/docker-compose.dev.yml exec backend python dev/seed_test_data.py
"""

import json
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import DB_PATH
from src.database.models import create_engine_from_path, init_db
from src.database.session_db import create_research_session, update_research_session
from src.database.conversation_db import save_turn
from src.database.results_db import save_workflow_result, save_verified_compounds


def seed():
    engine = create_engine_from_path(DB_PATH)
    init_db(engine)

    # Use a synthetic auth session ID for demo data
    auth_session_id = "demo-seed-session"

    with engine.connect() as conn:
        rs_id = create_research_session(
            conn,
            auth_session_id=auth_session_id,
            provider="anthropic",
            model="claude-sonnet-4-6",
            name="Demo: S. aureus GyrB",
        )
        update_research_session(
            conn, rs_id,
            organism="Staphylococcus aureus",
            target_protein="GyrB",
            uniprot_id="P0A749",
            pdb_id="4P8O",
            chembl_target_id="CHEMBL2095192",
            pipeline_stage="controls",
        )

        # Seed a short conversation
        save_turn(conn, rs_id, 0, "user",
                  [{"type": "text", "text": "Evaluate Staphylococcus aureus GyrB as a drug target"}])
        save_turn(conn, rs_id, 1, "assistant",
                  [{"type": "text", "text": "[WORKFLOW COMPLETE: evaluate_target]\nTarget: Staphylococcus aureus / GyrB\nRecommendation: GO. UniProt P0A749; best structure 4P8O at 1.95 Å (co-crystallized with novobiocin). Essential gene (ts mutant lethal). Five criteria all pass."}])
        save_turn(conn, rs_id, 2, "user",
                  [{"type": "text", "text": "Now generate validated controls"}])

        # Seed workflow result
        wr_id = save_workflow_result(
            conn, rs_id,
            workflow_type="evaluate_target",
            result={"recommendation": "GO", "uniprot_id": "P0A749", "best_pdb_id": "4P8O"},
            model_used="claude-sonnet-4-6",
            is_verified=True,
        )

        # Seed a few verified compounds
        save_verified_compounds(conn, wr_id, rs_id, [
            {
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
                "notes": "Clinical aminocoumarin antibiotic, ATP-competitive GyrB inhibitor",
            },
            {
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
                "notes": "Most potent natural aminocoumarin; 3-Cl group key for potency",
            },
        ])

    print(f"Seeded research session: {rs_id}")
    print(f"Target: S. aureus GyrB  |  UniProt P0A749  |  PDB 4P8O")
    print(f"Auth session: {auth_session_id}")
    print(f"DB path: {DB_PATH}")


if __name__ == "__main__":
    seed()
