"""Local RDKit cheminformatics tools. No network calls."""

from __future__ import annotations

_RDKIT_AVAILABLE = False
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors, FilterCatalog
    from rdkit.Chem.Scaffolds import MurckoScaffold
    _RDKIT_AVAILABLE = True
except ImportError:
    pass


def _rdkit_required(fn_name: str) -> dict:
    return {
        "error": f"rdkit-pypi not installed. Run: pip install rdkit-pypi. "
                 f"Function: {fn_name}"
    }


def validate_smiles(smiles: str) -> dict:
    """Validate a SMILES string and compute basic Lipinski properties.

    Returns {valid, canonical_smiles, mw, logp, hbd, hba, tpsa, rotatable_bonds,
             ro5_violations, error}.
    """
    if not _RDKIT_AVAILABLE:
        return _rdkit_required("validate_smiles")
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"valid": False, "smiles": smiles, "error": "Invalid SMILES"}
        mw = Descriptors.ExactMolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = rdMolDescriptors.CalcNumHBD(mol)
        hba = rdMolDescriptors.CalcNumHBA(mol)
        tpsa = Descriptors.TPSA(mol)
        rot = rdMolDescriptors.CalcNumRotatableBonds(mol)
        violations = sum([mw > 500, logp > 5, hbd > 5, hba > 10])
        return {
            "valid": True,
            "smiles": smiles,
            "canonical_smiles": Chem.MolToSmiles(mol),
            "mw": round(mw, 2),
            "logp": round(logp, 2),
            "hbd": hbd,
            "hba": hba,
            "tpsa": round(tpsa, 2),
            "rotatable_bonds": rot,
            "ro5_violations": violations,
        }
    except Exception as e:
        return {"valid": False, "smiles": smiles, "error": str(e)}


def calculate_molecular_properties(smiles_list: list[str]) -> dict:
    """Batch Lipinski + shape properties for a list of SMILES.

    Returns list of property dicts, one per input SMILES.
    """
    if not _RDKIT_AVAILABLE:
        return _rdkit_required("calculate_molecular_properties")
    results = []
    for smi in smiles_list:
        results.append(validate_smiles(smi))
    return {"results": results, "count": len(results)}


def screen_pains(smiles_list: list[str]) -> dict:
    """Apply PAINS filters (A, B, C) to a list of SMILES.

    Returns list of {smiles, is_pains, pains_alerts}.
    """
    if not _RDKIT_AVAILABLE:
        return _rdkit_required("screen_pains")

    params = FilterCatalog.FilterCatalogParams()
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_A)
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_B)
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_C)
    catalog = FilterCatalog.FilterCatalog(params)

    results = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            results.append({"smiles": smi, "is_pains": None, "pains_alerts": [], "error": "Invalid SMILES"})
            continue
        entries = catalog.GetMatches(mol)
        alerts = [e.GetDescription() for e in entries]
        results.append({
            "smiles": smi,
            "canonical_smiles": Chem.MolToSmiles(mol),
            "is_pains": bool(alerts),
            "pains_alerts": alerts,
        })
    return {"results": results, "pains_count": sum(1 for r in results if r.get("is_pains"))}


def compute_murcko_scaffolds(smiles_list: list[str]) -> dict:
    """Cluster compounds by Murcko scaffold.

    Returns {clusters: [{scaffold_smiles, members, count}]} sorted by cluster size desc.
    """
    if not _RDKIT_AVAILABLE:
        return _rdkit_required("compute_murcko_scaffolds")

    scaffold_map: dict[str, list[str]] = {}
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        key = Chem.MolToSmiles(scaffold) if scaffold else "__none__"
        scaffold_map.setdefault(key, []).append(smi)

    clusters = [
        {"scaffold_smiles": k, "members": v, "count": len(v)}
        for k, v in sorted(scaffold_map.items(), key=lambda x: -len(x[1]))
    ]
    return {"clusters": clusters, "total_scaffolds": len(clusters)}


def generate_decoys(
    positive_smiles_list: list[str],
    num_decoys_per_compound: int = 3,
    mw_tolerance: float = 25.0,
    logp_tolerance: float = 1.0,
) -> dict:
    """Generate property-matched decoy SMILES using DUD-E approach.

    Decoys match MW/logP/HBD/HBA of positives but differ structurally.
    Returns {positives_processed, decoy_strategy, note}.
    Note: This returns a *specification* for decoy queries; actual retrieval
    uses pubchem_similarity_search with inverted Tanimoto (low similarity, similar properties).
    """
    if not _RDKIT_AVAILABLE:
        return _rdkit_required("generate_decoys")

    specs = []
    for smi in positive_smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            continue
        mw = round(Descriptors.ExactMolWt(mol), 1)
        logp = round(Descriptors.MolLogP(mol), 2)
        hbd = rdMolDescriptors.CalcNumHBD(mol)
        hba = rdMolDescriptors.CalcNumHBA(mol)
        specs.append({
            "source_smiles": smi,
            "mw_range": [mw - mw_tolerance, mw + mw_tolerance],
            "logp_range": [logp - logp_tolerance, logp + logp_tolerance],
            "hbd": hbd,
            "hba": hba,
            "strategy": "pubchem_similarity_search with threshold=40 (low similarity) "
                        "then filter by property ranges above",
        })

    return {
        "positives_processed": len(specs),
        "decoy_specs": specs,
        "note": (
            "Use pubchem_similarity_search(smiles, threshold=40) per positive control, "
            "then filter results by the mw_range and logp_range above to get property-matched, "
            "structurally dissimilar decoys."
        ),
    }
