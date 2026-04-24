"""
Workflow 1: Evaluate Target Protein

Assess whether a protein is a viable drug target using 5 criteria:
1. Essentiality (essential to pathogen?)
2. Structural availability (structure known?)
3. Biochemical assay feasibility
4. Purification feasibility
5. Literature novelty
"""

from typing import Optional, Dict, Any
from src import DrugDiscoveryClient


def evaluate_target_workflow(
    organism: str,
    protein_name: str,
    protein_id: Optional[str] = None,
    client: Optional[DrugDiscoveryClient] = None,
) -> Dict[str, Any]:
    """
    Evaluate a protein as a drug target.

    Args:
        organism: Bacterial or protozoan species (e.g., "Staphylococcus aureus")
        protein_name: Common or systematic protein name (e.g., "DNA gyrase subunit B")
        protein_id: Optional UniProt ID or PDB code
        client: Optional DrugDiscoveryClient instance (auto-creates if None)

    Returns:
        {
            "status": "success",
            "task": "evaluate_target",
            "organism": organism,
            "protein": protein_name,
            "protein_id": protein_id or None,
            "assessment": {
                "essentiality": "...",
                "structure": "...",
                "assay": "...",
                "purification": "...",
                "novelty": "...",
                "recommendation": "GO" | "NO-GO"
            },
            "response": "Full assessment text from LLM"
        }
    """
    if client is None:
        client = DrugDiscoveryClient()

    # Call the DrugDiscoveryClient method
    result = client.evaluate_target(
        organism=organism,
        protein_name=protein_name,
        protein_id=protein_id,
    )

    # Return structured output
    return {
        "status": "success",
        "task": result.get("task", "evaluate_target"),
        "organism": result.get("organism", organism),
        "protein": result.get("protein", protein_name),
        "protein_id": protein_id,
        "response": result.get("response", ""),
    }
