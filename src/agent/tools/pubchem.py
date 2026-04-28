"""PubChem REST API tool functions."""

import httpx

_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_TIMEOUT = 15.0

_DEFAULT_PROPS = [
    "MolecularWeight", "XLogP", "TPSA",
    "IsomericSMILES", "HBondDonorCount", "HBondAcceptorCount",
    "RotatableBondCount", "IUPACName",
]


async def pubchem_compound_lookup(
    identifier: str,
    identifier_type: str = "name",
    properties: list[str] | None = None,
) -> dict:
    """Look up a compound by name, CID, SMILES, or InChIKey.

    Returns verified CID, canonical SMILES, and Lipinski properties.
    identifier_type: 'name' | 'cid' | 'smiles' | 'inchikey'
    """
    props = ",".join(properties or _DEFAULT_PROPS)
    if identifier_type == "smiles":
        url = f"{_BASE}/compound/fastsimilarity_2d/smiles/property/{props}/JSON"
        params = {"smiles": identifier, "Threshold": 100, "MaxRecords": 1}
    else:
        enc = httpx.URL("").copy_with(path=f"/{identifier}").path.lstrip("/")
        url = f"{_BASE}/compound/{identifier_type}/{identifier}/property/{props}/JSON"
        params = {}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    props_list = data.get("PropertyTable", {}).get("Properties", [])
    if not props_list:
        return {"found": False, "identifier": identifier}

    p = props_list[0]
    return {
        "found": True,
        "cid": p.get("CID"),
        "name": identifier if identifier_type == "name" else None,
        "smiles": p.get("IsomericSMILES"),
        "mw": p.get("MolecularWeight"),
        "xlogp": p.get("XLogP"),
        "tpsa": p.get("TPSA"),
        "hbd": p.get("HBondDonorCount"),
        "hba": p.get("HBondAcceptorCount"),
        "rotatable_bonds": p.get("RotatableBondCount"),
        "iupac_name": p.get("IUPACName"),
    }


async def pubchem_bioactivity_search(
    target_gene_symbol: str,
    assay_type: str = "IC50",
    activity_cutoff_um: float = 10.0,
    max_results: int = 20,
) -> dict:
    """Find compounds with measured activity against a target gene.

    Returns list of {cid, name, smiles, activity_value_nm, activity_units, assay_id}.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        aids_url = f"{_BASE}/assay/target/genesymbol/{target_gene_symbol}/aids/JSON"
        r = await client.get(aids_url)
        if r.status_code == 404:
            return {"found": False, "gene": target_gene_symbol, "compounds": []}
        r.raise_for_status()
        aids = r.json().get("IdentifierList", {}).get("AID", [])[:5]

        compounds = []
        for aid in aids:
            act_url = f"{_BASE}/assay/aid/{aid}/concise/JSON"
            ar = await client.get(act_url)
            if ar.status_code != 200:
                continue
            rows = ar.json().get("Table", {}).get("Row", [])
            for row in rows[:max_results]:
                cells = row.get("Cell", [])
                if len(cells) < 5:
                    continue
                try:
                    val_nm = float(cells[4]) * 1000  # µM → nM approximation
                    if val_nm > activity_cutoff_um * 1000:
                        continue
                except (ValueError, TypeError):
                    continue
                compounds.append({
                    "cid": cells[0],
                    "name": cells[1] if len(cells) > 1 else None,
                    "smiles": None,
                    "activity_value_nm": val_nm,
                    "activity_units": "nM",
                    "assay_id": aid,
                })
                if len(compounds) >= max_results:
                    break
            if len(compounds) >= max_results:
                break

    return {"found": bool(compounds), "gene": target_gene_symbol, "compounds": compounds}


async def pubchem_similarity_search(
    smiles: str,
    threshold: int = 85,
    max_results: int = 10,
) -> dict:
    """Find structurally similar compounds by 2D Tanimoto similarity.

    Used to find property-matched decoys for controls generation.
    Returns list of {cid, similarity_score}.
    """
    url = f"{_BASE}/compound/fastsimilarity_2d/smiles/cids/JSON"
    params = {"smiles": smiles, "Threshold": threshold, "MaxRecords": max_results}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(url, params=params)
        if r.status_code == 404:
            return {"found": False, "cids": []}
        r.raise_for_status()
        cids = r.json().get("IdentifierList", {}).get("CID", [])

    return {"found": bool(cids), "cids": cids[:max_results]}
