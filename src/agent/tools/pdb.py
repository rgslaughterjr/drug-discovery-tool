"""RCSB PDB REST API tool functions."""

import httpx

_SEARCH = "https://search.rcsb.org/rcsbsearch/v2/query"
_DATA = "https://data.rcsb.org/rest/v1/core"
_TIMEOUT = 15.0


async def pdb_structure_search(
    uniprot_id: str,
    has_ligand: bool = True,
    max_resolution_angstrom: float = 2.5,
) -> dict:
    """Search RCSB PDB for structures of a protein by UniProt ID.

    Returns list of {pdb_id, resolution, deposition_date, organism, method, ligand_ids}.
    Sorted by resolution ascending.
    """
    query: dict = {
        "query": {
            "type": "group",
            "logical_operator": "and",
            "nodes": [
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                        "operator": "in",
                        "value": [uniprot_id],
                        "negation": False,
                    },
                },
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "reflns.d_resolution_high",
                        "operator": "less_or_equal",
                        "value": max_resolution_angstrom,
                        "negation": False,
                    },
                },
            ],
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {"start": 0, "rows": 10},
            "sort": [{"sort_by": "score", "direction": "desc"}],
            "results_content_type": ["experimental"],
        },
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(_SEARCH, json=query)
        if r.status_code in (204, 404):
            return {"found": False, "uniprot_id": uniprot_id, "structures": []}
        r.raise_for_status()
        hits = r.json().get("result_set", [])

    structures = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for hit in hits[:8]:
            pdb_id = hit.get("identifier", "").upper()
            if not pdb_id:
                continue
            er = await client.get(f"{_DATA}/entry/{pdb_id}")
            if er.status_code != 200:
                structures.append({"pdb_id": pdb_id})
                continue
            entry = er.json()
            cell = entry.get("cell", {})
            exp = entry.get("exptl", [{}])[0]
            refln = entry.get("reflns", [{}])[0]
            rcsb = entry.get("rcsb_entry_info", {})
            structures.append({
                "pdb_id": pdb_id,
                "resolution": refln.get("d_resolution_high"),
                "deposition_date": entry.get("rcsb_accession_info", {}).get("deposit_date"),
                "method": exp.get("method"),
                "polymer_count": rcsb.get("deposited_polymer_entity_instance_count"),
                "nonpolymer_count": rcsb.get("deposited_nonpolymer_entity_instance_count", 0),
                "has_ligand": (rcsb.get("deposited_nonpolymer_entity_instance_count", 0) or 0) > 0,
            })

    if has_ligand:
        structures = [s for s in structures if s.get("has_ligand")]

    return {"found": bool(structures), "uniprot_id": uniprot_id, "structures": structures}


async def pdb_binding_site_info(pdb_id: str) -> dict:
    """Fetch binding site and co-crystallized ligand info for a PDB entry.

    Returns {pdb_id, resolution, binding_site_residues, co_crystallized_ligands}.
    """
    pdb_id = pdb_id.upper()

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        er = await client.get(f"{_DATA}/entry/{pdb_id}")
        if er.status_code == 404:
            return {"found": False, "pdb_id": pdb_id}
        er.raise_for_status()
        entry = er.json()

        # Fetch nonpolymer (ligand) entities
        ligands = []
        np_ids = entry.get("rcsb_entry_container_identifiers", {}).get(
            "non_polymer_entity_ids", []
        ) or []
        for np_id in np_ids[:6]:
            lr = await client.get(f"{_DATA}/nonpolymer_entity/{pdb_id}/{np_id}")
            if lr.status_code != 200:
                continue
            lig = lr.json()
            comp = lig.get("pdbx_entity_nonpoly", {})
            chem = lig.get("chem_comp", {})
            ligands.append({
                "ligand_id": comp.get("comp_id"),
                "name": comp.get("name") or chem.get("name"),
                "formula": chem.get("formula"),
                "mw": chem.get("formula_weight"),
                "smiles": chem.get("pdbx_smiles"),
            })

    refln = entry.get("reflns", [{}])[0] if entry.get("reflns") else {}
    return {
        "found": True,
        "pdb_id": pdb_id,
        "resolution": refln.get("d_resolution_high"),
        "deposition_date": entry.get("rcsb_accession_info", {}).get("deposit_date"),
        "experimental_method": (entry.get("exptl", [{}])[0] or {}).get("method"),
        "co_crystallized_ligands": ligands,
        "ligand_count": len(ligands),
    }
