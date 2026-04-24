"""
Workflow 3: Prepare Screening Campaign

Design a pharmacophore-based screening campaign using ChemBridge Diversity
and ZINC20 database with physicochemical filters and PAINS exclusion.
"""

from typing import Optional, Dict, Any
from src import DrugDiscoveryClient


def prep_screening_workflow(
    organism: str,
    protein_name: str,
    pdb_id: str,
    mechanism: str,
    docking_software: Optional[str] = None,
    client: Optional[DrugDiscoveryClient] = None,
) -> Dict[str, Any]:
    """
    Prepare a screening campaign for a target protein.

    Args:
        organism: Target organism
        protein_name: Target protein name
        pdb_id: PDB structure ID
        mechanism: Binding mechanism (e.g., "competitive NADPH inhibition")
        docking_software: Docking software (Autodock Vina, DOCK6, Glide, rDock)
        client: Optional DrugDiscoveryClient instance (auto-creates if None)

    Returns:
        {
            "status": "success",
            "task": "prep_screening",
            "organism": organism,
            "protein": protein_name,
            "pdb_id": pdb_id,
            "mechanism": mechanism,
            "pharmacophore": [...],
            "filters": {...},
            "zinc_query": "...",
            "response": "Full screening brief from LLM"
        }
    """
    if client is None:
        client = DrugDiscoveryClient()

    result = client.prep_screening(
        organism=organism,
        protein_name=protein_name,
        pdb_id=pdb_id,
        mechanism=mechanism,
        docking_software=docking_software,
    )

    return {
        "status": "success",
        "task": result.get("task", "prep_screening"),
        "organism": result.get("organism", organism),
        "protein": result.get("protein", protein_name),
        "pdb_id": result.get("pdb_id", pdb_id),
        "mechanism": result.get("mechanism", mechanism),
        "response": result.get("response", ""),
    }
