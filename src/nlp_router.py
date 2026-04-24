"""
Natural Language Router: Map user input to workflows.

Simple keyword-based routing (no extra API calls).
"""

import re
from typing import Optional, Tuple, Dict, Any


def route_user_input(user_message: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Route user message to appropriate workflow.

    Args:
        user_message: Natural language input from user

    Returns:
        (workflow_name, extracted_params) or None if unrecognized

    Example:
        "Evaluate S. aureus GyrB with PDB 4P8O" ->
        ("evaluate-target", {"organism": "S. aureus", "protein_name": "GyrB", ...})
    """
    message_lower = user_message.lower()

    # Route 1: Evaluate Target
    if any(w in message_lower for w in ["evaluate", "assess", "target", "drug target"]):
        params = _extract_evaluate_params(user_message)
        if params.get("organism") and params.get("protein_name"):
            return ("evaluate-target", params)

    # Route 2: Get Controls
    if any(w in message_lower for w in ["control", "validation", "positive", "negative", "decoy"]):
        params = _extract_controls_params(user_message)
        if params.get("organism") and params.get("protein_name") and params.get("pdb_id"):
            return ("get-controls", params)

    # Route 3: Prep Screening
    if any(w in message_lower for w in ["screening", "pharmacophore", "zinc", "chembridge", "prepare"]):
        params = _extract_screening_params(user_message)
        if params.get("organism") and params.get("protein_name") and params.get("pdb_id"):
            return ("prep-screening", params)

    # Route 4: Analyze Hits
    if any(w in message_lower for w in ["analyze", "hits", "prioritize", "rank", "docking", "score"]):
        params = _extract_hits_params(user_message)
        if params.get("protein_name") and params.get("num_compounds"):
            return ("analyze-hits", params)

    return None


def _extract_evaluate_params(message: str) -> Dict[str, Any]:
    """Extract parameters for evaluate-target workflow."""
    params = {}

    # Extract organism (often before "/" or after common keywords)
    organism_match = re.search(r"(?:organism|species|bacterial|bacteria|protozoan)[\s:]*([^/\n]+)", message, re.I)
    if organism_match:
        params["organism"] = organism_match.group(1).strip()
    else:
        # Fallback: first capitalized phrase
        words = message.split()
        for i, word in enumerate(words):
            if word[0].isupper() and i < len(words) - 1:
                potential = " ".join(words[i:i+2])
                if len(potential) > 5:
                    params["organism"] = potential.strip(".,")
                    break

    # Extract protein name
    protein_match = re.search(r"(?:protein|subunit)[\s:]*([^,/\n]+)", message, re.I)
    if protein_match:
        params["protein_name"] = protein_match.group(1).strip()

    # Extract protein ID (common abbreviations like GyrB, DHFR)
    pdb_match = re.search(r"(?:protein[\s_]?id|pdb|uniprot)[\s:]*([A-Z0-9]+)", message, re.I)
    if pdb_match:
        params["protein_id"] = pdb_match.group(1).strip()

    return params


def _extract_controls_params(message: str) -> Dict[str, Any]:
    """Extract parameters for get-controls workflow."""
    params = _extract_evaluate_params(message)  # Reuse organism/protein extraction

    # Extract PDB ID
    pdb_match = re.search(r"(?:pdb|structure)[\s:]*([0-9A-Z]+)", message, re.I)
    if pdb_match:
        params["pdb_id"] = pdb_match.group(1).strip().upper()

    return params


def _extract_screening_params(message: str) -> Dict[str, Any]:
    """Extract parameters for prep-screening workflow."""
    params = _extract_controls_params(message)  # Reuse PDB extraction

    # Extract mechanism
    mech_match = re.search(r"(?:mechanism|inhibition|binding)[\s:]*([^,.\n]+)", message, re.I)
    if mech_match:
        params["mechanism"] = mech_match.group(1).strip()

    # Extract docking software
    docking_keywords = ["vina", "autodock", "dock6", "glide", "rdock"]
    for keyword in docking_keywords:
        if keyword in message.lower():
            params["docking_software"] = keyword.title()
            break

    return params


def _extract_hits_params(message: str) -> Dict[str, Any]:
    """Extract parameters for analyze-hits workflow."""
    params = {}

    # Extract protein name
    protein_match = re.search(r"(?:protein|target)[\s:]*([^,/\n]+)", message, re.I)
    if protein_match:
        params["protein_name"] = protein_match.group(1).strip()

    # Extract number of compounds (look for numbers followed by "compounds" or "screened")
    num_match = re.search(r"(\d+,?\d*)\s*(?:compounds|screened)", message, re.I)
    if num_match:
        num_str = num_match.group(1).replace(",", "")
        params["num_compounds"] = int(num_str)

    # Placeholder for score distribution (would need more context)
    score_match = re.search(r"(?:mean|score)[\s:]*([^,\n]+)", message, re.I)
    if score_match:
        params["docking_scores_summary"] = score_match.group(1).strip()

    return params
