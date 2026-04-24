"""
Workflow 4: Analyze Virtual Screening Hits

Prioritize and rank compounds from virtual screening for wet-lab validation.
Anchors score cutoffs to positive controls and applies PAINS re-filtering.
"""

from typing import Optional, Dict, Any
from src import DrugDiscoveryClient


def analyze_hits_workflow(
    protein_name: str,
    num_compounds: int,
    docking_scores_summary: str,
    positive_controls_affinity: Optional[str] = None,
    client: Optional[DrugDiscoveryClient] = None,
) -> Dict[str, Any]:
    """
    Analyze and prioritize hits from virtual screening.

    Args:
        protein_name: Name of target protein
        num_compounds: Total number of compounds screened
        docking_scores_summary: Summary of docking score distribution
        positive_controls_affinity: Affinity data for positive controls (optional)
        client: Optional DrugDiscoveryClient instance (auto-creates if None)

    Returns:
        {
            "status": "success",
            "task": "analyze_hits",
            "protein": protein_name,
            "num_screened": num_compounds,
            "score_cutoff": "...",
            "scaffolds": [...],
            "purchase_list": [...],
            "response": "Full hit analysis from LLM"
        }
    """
    if client is None:
        client = DrugDiscoveryClient()

    result = client.analyze_hits(
        protein_name=protein_name,
        num_compounds=num_compounds,
        docking_scores_summary=docking_scores_summary,
        positive_controls_affinity=positive_controls_affinity,
    )

    return {
        "status": "success",
        "task": result.get("task", "analyze_hits"),
        "protein": result.get("protein", protein_name),
        "num_screened": result.get("num_screened", num_compounds),
        "response": result.get("response", ""),
    }
