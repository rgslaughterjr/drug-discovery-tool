"""Export endpoints for research session data."""

from __future__ import annotations

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.engine import Engine

from src.database.results_db import get_verified_compounds, get_workflow_results
from src.database.session_db import get_research_session
from src.session_manager import _store as session_store

router = APIRouter(prefix="/api/export", tags=["export"])


def _require_session(x_session_id: str | None) -> None:
    if not x_session_id or not session_store.get(x_session_id):
        raise HTTPException(status_code=401, detail="Session expired or invalid")


@router.get("/{rs_id}/compounds.csv")
async def export_compounds_csv(
    rs_id: str,
    request: Request,
    workflow_type: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None),
):
    """Export verified compounds as CSV."""
    _require_session(x_session_id)
    engine: Engine = request.app.state.db_engine

    with engine.connect() as conn:
        session = get_research_session(conn, rs_id)
        if not session or session["auth_session_id"] != x_session_id:
            raise HTTPException(status_code=404, detail="Research session not found")
        compounds = get_verified_compounds(conn, rs_id, compound_type=workflow_type)

    if not compounds:
        raise HTTPException(status_code=404, detail="No compounds found for this session")

    output = io.StringIO()
    fieldnames = [
        "rank", "name", "compound_type", "pubchem_cid", "chembl_id",
        "smiles", "canonical_smiles", "mw", "logp", "tpsa", "hbd", "hba",
        "activity_value_nm", "activity_type", "is_pains", "pains_alerts",
        "docking_score", "notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(compounds)

    protein = session.get("target_protein", "unknown").replace(" ", "_")
    filename = f"{protein}_compounds.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{rs_id}/results.json")
async def export_results_json(
    rs_id: str,
    request: Request,
    x_session_id: Optional[str] = Header(None),
):
    """Export full research session as JSON."""
    _require_session(x_session_id)
    engine: Engine = request.app.state.db_engine

    with engine.connect() as conn:
        session = get_research_session(conn, rs_id)
        if not session or session["auth_session_id"] != x_session_id:
            raise HTTPException(status_code=404, detail="Research session not found")
        results = get_workflow_results(conn, rs_id)
        compounds = get_verified_compounds(conn, rs_id)

    # Parse stored JSON columns
    for r in results:
        try:
            r["result"] = json.loads(r.pop("result_json", "{}"))
        except (json.JSONDecodeError, KeyError):
            pass
        r.pop("tool_calls_json", None)  # omit verbose audit log from export

    export = {
        "research_session": {k: str(v) for k, v in session.items()},
        "workflow_results": results,
        "verified_compounds": compounds,
    }
    return JSONResponse(content=export)
