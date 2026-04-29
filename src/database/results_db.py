"""WorkflowResult and VerifiedCompound CRUD operations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.engine import Connection

from .models import verified_compounds, workflow_results


def save_workflow_result(
    conn: Connection,
    research_session_id: str,
    workflow_type: str,
    result: dict,
    model_used: str,
    tool_calls: list[dict] | None = None,
    is_verified: bool = False,
) -> str:
    """Persist a workflow result. Returns the new result UUID."""
    wr_id = str(uuid.uuid4())
    conn.execute(
        workflow_results.insert().values(
            id=wr_id,
            research_session_id=research_session_id,
            workflow_type=workflow_type,
            result_json=json.dumps(result),
            tool_calls_json=json.dumps(tool_calls or []),
            model_used=model_used,
            created_at=datetime.utcnow(),
            is_verified=is_verified,
        )
    )
    conn.commit()
    return wr_id


def save_verified_compounds(
    conn: Connection,
    workflow_result_id: str,
    research_session_id: str,
    compounds: list[dict],
) -> None:
    """Bulk-insert verified compound rows."""
    for c in compounds:
        conn.execute(
            verified_compounds.insert().values(
                workflow_result_id=workflow_result_id,
                research_session_id=research_session_id,
                compound_type=c.get("compound_type", "unknown"),
                name=c.get("name"),
                pubchem_cid=c.get("pubchem_cid") or c.get("cid"),
                chembl_id=c.get("chembl_id"),
                smiles=c.get("smiles", ""),
                canonical_smiles=c.get("canonical_smiles"),
                mw=c.get("mw"),
                logp=c.get("logp") or c.get("xlogp"),
                tpsa=c.get("tpsa"),
                hbd=c.get("hbd"),
                hba=c.get("hba"),
                activity_value_nm=c.get("activity_value_nm") or c.get("activity_nm"),
                activity_type=c.get("activity_type"),
                is_pains=c.get("is_pains"),
                pains_alerts=",".join(c.get("pains_alerts", [])) if c.get("pains_alerts") else None,
                docking_score=c.get("docking_score"),
                rank=c.get("rank"),
                notes=c.get("notes"),
            )
        )
    conn.commit()


def get_workflow_results(
    conn: Connection,
    research_session_id: str,
    workflow_type: str | None = None,
) -> list[dict]:
    q = select(workflow_results).where(
        workflow_results.c.research_session_id == research_session_id
    )
    if workflow_type:
        q = q.where(workflow_results.c.workflow_type == workflow_type)
    q = q.order_by(workflow_results.c.created_at.desc())
    rows = conn.execute(q).mappings().all()
    return [dict(r) for r in rows]


def get_verified_compounds(
    conn: Connection,
    research_session_id: str,
    compound_type: str | None = None,
) -> list[dict]:
    q = select(verified_compounds).where(
        verified_compounds.c.research_session_id == research_session_id
    )
    if compound_type:
        q = q.where(verified_compounds.c.compound_type == compound_type)
    q = q.order_by(verified_compounds.c.rank.asc())
    rows = conn.execute(q).mappings().all()
    return [dict(r) for r in rows]


def delete_results(conn: Connection, research_session_id: str) -> None:
    conn.execute(
        delete(workflow_results)
        .where(workflow_results.c.research_session_id == research_session_id)
    )
    conn.commit()
