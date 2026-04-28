"""UniProt REST API tool functions."""

import httpx

_BASE = "https://rest.uniprot.org/uniprotkb"
_TIMEOUT = 15.0


async def uniprot_search(
    query: str,
    reviewed: bool = True,
    max_results: int = 5,
) -> dict:
    """Search UniProt for proteins by name/organism query.

    Returns list of {uniprot_id, gene_name, organism, function, sequence_length}.
    reviewed=True restricts to Swiss-Prot curated entries.
    """
    q = f"({query})"
    if reviewed:
        q += " AND (reviewed:true)"

    params = {
        "query": q,
        "format": "json",
        "size": max_results,
        "fields": "accession,gene_names,organism_name,protein_name,length,go",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(f"{_BASE}/search", params=params)
        r.raise_for_status()
        data = r.json()

    results = []
    for entry in data.get("results", []):
        genes = entry.get("genes", [])
        gene_name = genes[0].get("geneName", {}).get("value") if genes else None
        protein_desc = entry.get("proteinDescription", {})
        prot_name = (
            protein_desc.get("recommendedName", {}).get("fullName", {}).get("value")
            or protein_desc.get("submissionNames", [{}])[0].get("fullName", {}).get("value")
        )
        go_terms = [
            g.get("properties", {}).get("term")
            for g in entry.get("uniProtKBCrossReferences", [])
            if g.get("database") == "GO"
        ][:5]
        results.append({
            "uniprot_id": entry.get("primaryAccession"),
            "gene_name": gene_name,
            "protein_name": prot_name,
            "organism": entry.get("organism", {}).get("scientificName"),
            "sequence_length": entry.get("sequence", {}).get("length"),
            "go_terms": go_terms,
        })

    return {"found": bool(results), "query": query, "entries": results}


async def uniprot_entry_detail(uniprot_id: str) -> dict:
    """Fetch detailed UniProt record for a single accession.

    Returns function text, subcellular location, GO terms, and known inhibitor notes.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.get(
            f"{_BASE}/{uniprot_id}",
            params={"format": "json"},
        )
        if r.status_code == 404:
            return {"found": False, "uniprot_id": uniprot_id}
        r.raise_for_status()
        data = r.json()

    # Extract function comment
    comments = data.get("comments", [])
    function_text = next(
        (c.get("texts", [{}])[0].get("value", "")
         for c in comments if c.get("commentType") == "FUNCTION"),
        None,
    )
    subcell = next(
        (c.get("subcellularLocations", [{}])[0]
          .get("location", {}).get("value")
         for c in comments if c.get("commentType") == "SUBCELLULAR LOCATION"),
        None,
    )
    essentiality = next(
        (c.get("texts", [{}])[0].get("value", "")
         for c in comments if c.get("commentType") == "DISRUPTION PHENOTYPE"),
        None,
    )

    go_terms = {}
    for xref in data.get("uniProtKBCrossReferences", []):
        if xref.get("database") == "GO":
            for prop in xref.get("properties", []):
                if prop.get("key") == "GoTerm":
                    aspect, term = prop["value"].split(":", 1)
                    go_terms.setdefault(aspect.strip(), []).append(term.strip())

    genes = data.get("genes", [])
    gene_name = genes[0].get("geneName", {}).get("value") if genes else None

    return {
        "found": True,
        "uniprot_id": uniprot_id,
        "gene_name": gene_name,
        "organism": data.get("organism", {}).get("scientificName"),
        "protein_name": (
            data.get("proteinDescription", {})
                .get("recommendedName", {})
                .get("fullName", {})
                .get("value")
        ),
        "function": function_text,
        "subcellular_location": subcell,
        "essentiality_phenotype": essentiality,
        "go_biological_process": go_terms.get("P", [])[:5],
        "go_molecular_function": go_terms.get("F", [])[:5],
        "sequence_length": data.get("sequence", {}).get("length"),
    }
