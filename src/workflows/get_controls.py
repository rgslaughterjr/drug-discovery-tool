"""
Workflow 2: Generate Validation Controls

Generate 10 known positive controls (binders) and 10 property-matched negative
controls (DUD-E decoys) to validate docking software accuracy.
"""

from typing import Optional, Dict, Any
from src import DrugDiscoveryClient


def get_controls_workflow(
    organism: str,
    protein_name: str,
    pdb_id: str,
    client: Optional[DrugDiscoveryClient] = None,
) -> Dict[str, Any]:
    """
    Generate validation controls for a target protein.

    Args:
        organism: Species containing target protein
        protein_name: Name of target protein
        pdb_id: PDB structure ID (e.g., "4P8O")
        client: Optional DrugDiscoveryClient instance (auto-creates if None)

    Returns:
        {
            "status": "success",
            "task": "get_controls",
            "organism": organism,
            "protein": protein_name,
            "pdb_id": pdb_id,
            "positive_controls": [{"compound": "...", "ic50": "...", ...}],
            "negative_controls": [{"compound": "...", "properties": {...}}],
            "response": "Full controls data from LLM"
        }
    """
    if client is None:
        client = DrugDiscoveryClient()

    result = client.get_controls(
        organism=organism,
        protein_name=protein_name,
        pdb_id=pdb_id,
    )

    return {
        "status": "success",
        "task": result.get("task", "get_controls"),
        "organism": result.get("organism", organism),
        "protein": result.get("protein", protein_name),
        "pdb_id": result.get("pdb_id", pdb_id),
        "response": result.get("response", ""),
    }
