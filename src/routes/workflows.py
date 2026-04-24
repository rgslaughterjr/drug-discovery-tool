"""Workflow route handlers."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
from src.session_manager import get_session_store
from src import DrugDiscoveryClient, APIConfig
from src.workflows import (
    evaluate_target_workflow,
    get_controls_workflow,
    prep_screening_workflow,
    analyze_hits_workflow,
)

router = APIRouter(prefix="/api/workflow", tags=["workflows"])


# Request/Response Models
class EvaluateTargetRequest(BaseModel):
    organism: str
    protein_name: str
    protein_id: Optional[str] = None


class GetControlsRequest(BaseModel):
    organism: str
    protein_name: str
    pdb_id: str


class PrepScreeningRequest(BaseModel):
    organism: str
    protein_name: str
    pdb_id: str
    mechanism: str
    docking_software: Optional[str] = None


class AnalyzeHitsRequest(BaseModel):
    protein_name: str
    num_compounds: int
    docking_scores_summary: str
    positive_controls_affinity: Optional[str] = None


def _get_session_client(session_id: str) -> DrugDiscoveryClient:
    """Create DrugDiscoveryClient from session credentials."""
    store = get_session_store()

    if not store.validate(session_id):
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    provider = store.get_provider(session_id)
    api_key = store.get_api_key(session_id)
    model = store.get_model(session_id)

    config = APIConfig(
        provider=provider,
        api_key=api_key,
        model=model,
    )
    return DrugDiscoveryClient(config=config)


def _add_session_info(result: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Add session expiry info to response."""
    store = get_session_store()
    expires_in = store.get_expires_in(session_id)
    result["session_expires_in"] = expires_in or 0
    return result


@router.post("/evaluate-target")
async def evaluate_target(
    request: EvaluateTargetRequest,
    x_session_id: str = Header(None),
):
    """Evaluate a protein as a drug target."""
    try:
        client = _get_session_client(x_session_id)
        result = evaluate_target_workflow(
            organism=request.organism,
            protein_name=request.protein_name,
            protein_id=request.protein_id,
            client=client,
        )
        return _add_session_info(result, x_session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")


@router.post("/get-controls")
async def get_controls(
    request: GetControlsRequest,
    x_session_id: str = Header(None),
):
    """Generate validation controls."""
    try:
        client = _get_session_client(x_session_id)
        result = get_controls_workflow(
            organism=request.organism,
            protein_name=request.protein_name,
            pdb_id=request.pdb_id,
            client=client,
        )
        return _add_session_info(result, x_session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")


@router.post("/prep-screening")
async def prep_screening(
    request: PrepScreeningRequest,
    x_session_id: str = Header(None),
):
    """Prepare screening campaign."""
    try:
        client = _get_session_client(x_session_id)
        result = prep_screening_workflow(
            organism=request.organism,
            protein_name=request.protein_name,
            pdb_id=request.pdb_id,
            mechanism=request.mechanism,
            docking_software=request.docking_software,
            client=client,
        )
        return _add_session_info(result, x_session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")


@router.post("/analyze-hits")
async def analyze_hits(
    request: AnalyzeHitsRequest,
    x_session_id: str = Header(None),
):
    """Analyze and prioritize screening hits."""
    try:
        client = _get_session_client(x_session_id)
        result = analyze_hits_workflow(
            protein_name=request.protein_name,
            num_compounds=request.num_compounds,
            docking_scores_summary=request.docking_scores_summary,
            positive_controls_affinity=request.positive_controls_affinity,
            client=client,
        )
        return _add_session_info(result, x_session_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")
