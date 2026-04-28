"""ChEMBL REST API tool functions."""

import httpx

_BASE = "https://www.ebi.ac.uk/chembl/api/data"
_TIMEOUT = 20.0


async def chembl_target_search(
    target_name: str,
    organism: str = "",
) -> dict:
    """Search ChEMBL for a target by name and organism.

    Returns list of {chembl_id, target_type, pref_name, organism, protein_class}.
    """
    params: dict = {
        "pref_name__icontains": target_name,
        "format": "json",
        "limit": 5,
    }
    if organism:
        params["organism__icontains"] = organism

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(f"{_BASE}/target.json", params=params)
        r.raise_for_status()
        data = r.json()

    targets = []
    for t in data.get("targets", []):
        targets.append({
            "chembl_id": t.get("target_chembl_id"),
            "target_type": t.get("target_type"),
            "pref_name": t.get("pref_name"),
            "organism": t.get("organism"),
            "protein_class": t.get("target_components", [{}])[0]
                              .get("target_component_synonyms", [{}])[0]
                              .get("component_synonym") if t.get("target_components") else None,
        })
    return {"found": bool(targets), "targets": targets}


async def chembl_bioactivity(
    chembl_target_id: str,
    activity_type: str = "IC50",
    max_activity_nm: float = 10000.0,
    max_results: int = 20,
) -> dict:
    """Fetch bioactivity data for a ChEMBL target.

    Returns list of {compound_name, chembl_id, smiles, activity_nm, assay_description, doi}.
    """
    params = {
        "target_chembl_id": chembl_target_id,
        "standard_type": activity_type,
        "standard_value__lte": max_activity_nm,
        "standard_units": "nM",
        "format": "json",
        "limit": max_results,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(f"{_BASE}/activity.json", params=params)
        r.raise_for_status()
        data = r.json()

    compounds = []
    for a in data.get("activities", []):
        try:
            val = float(a.get("standard_value", 0))
        except (TypeError, ValueError):
            val = None
        compounds.append({
            "compound_name": a.get("molecule_pref_name") or a.get("compound_name"),
            "chembl_id": a.get("molecule_chembl_id"),
            "smiles": a.get("canonical_smiles"),
            "activity_nm": val,
            "activity_type": a.get("standard_type"),
            "assay_description": (a.get("assay_description") or "")[:120],
            "doi": a.get("document_chembl_id"),
            "pchembl": a.get("pchembl_value"),
        })
    return {"found": bool(compounds), "target": chembl_target_id, "compounds": compounds}


async def chembl_compound_detail(chembl_id: str) -> dict:
    """Fetch full compound record from ChEMBL.

    Returns {chembl_id, pref_name, smiles, mw, alogp, hba, hbd, psa, ro5_violations, qed}.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(f"{_BASE}/molecule/{chembl_id}.json")
        if r.status_code == 404:
            return {"found": False, "chembl_id": chembl_id}
        r.raise_for_status()
        data = r.json()

    props = data.get("molecule_properties") or {}
    return {
        "found": True,
        "chembl_id": data.get("molecule_chembl_id"),
        "pref_name": data.get("pref_name"),
        "smiles": data.get("molecule_structures", {}).get("canonical_smiles"),
        "mw": props.get("full_mwt"),
        "alogp": props.get("alogp"),
        "hba": props.get("hba"),
        "hbd": props.get("hbd"),
        "psa": props.get("psa"),
        "ro5_violations": props.get("num_ro5_violations"),
        "qed": props.get("qed_weighted"),
        "num_alerts": props.get("num_alerts"),
    }
