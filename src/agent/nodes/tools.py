"""
LangChain @tool wrappers for all 15 domain tools.
These are passed to the orchestrator and sub-agent nodes via bind_tools().
"""

from __future__ import annotations

from typing import List, Optional
from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# PubChem tools
# ---------------------------------------------------------------------------

@tool
async def pubchem_compound_lookup(identifier: str, identifier_type: str = "name") -> dict:
    """Look up a compound in PubChem by name, CID, SMILES, or InChIKey.

    Returns verified CID, canonical SMILES, and Lipinski properties.
    ALWAYS use this before reporting any compound data to confirm it is real.
    identifier_type: 'name' | 'cid' | 'smiles' | 'inchikey'
    """
    from src.agent.tools.pubchem import pubchem_compound_lookup as _fn
    return await _fn(identifier=identifier, identifier_type=identifier_type)


@tool
async def pubchem_bioactivity_search(
    target_gene_symbol: str,
    assay_type: str = "IC50",
    activity_cutoff_um: float = 10.0,
    max_results: int = 20,
) -> dict:
    """Search PubChem for compounds with measured activity against a gene target.

    Returns CIDs, names, activity values, and assay IDs.
    Use gene symbol (e.g. 'GYRB', 'DHFR') not full protein name.
    """
    from src.agent.tools.pubchem import pubchem_bioactivity_search as _fn
    return await _fn(
        target_gene_symbol=target_gene_symbol,
        assay_type=assay_type,
        activity_cutoff_um=activity_cutoff_um,
        max_results=max_results,
    )


@tool
async def pubchem_similarity_search(
    smiles: str,
    threshold: int = 85,
    max_results: int = 10,
) -> dict:
    """Find structurally similar compounds by 2D Tanimoto similarity.

    threshold=85-95 for similar analogs; threshold=30-50 for property-matched decoys.
    """
    from src.agent.tools.pubchem import pubchem_similarity_search as _fn
    return await _fn(smiles=smiles, threshold=threshold, max_results=max_results)


# ---------------------------------------------------------------------------
# ChEMBL tools
# ---------------------------------------------------------------------------

@tool
async def chembl_target_search(target_name: str, organism: Optional[str] = None) -> dict:
    """Search ChEMBL for a drug target by name and organism.

    Returns ChEMBL target IDs needed for chembl_bioactivity calls.
    Always call this first to get the chembl_target_id.
    """
    from src.agent.tools.chembl import chembl_target_search as _fn
    return await _fn(target_name=target_name, organism=organism)


@tool
async def chembl_bioactivity(
    chembl_target_id: str,
    activity_type: str = "IC50",
    max_activity_nm: float = 10000.0,
    max_results: int = 20,
) -> dict:
    """Fetch real bioactivity data (IC50/Ki) for a ChEMBL target.

    Returns verified compounds with SMILES, measured affinity, and literature DOIs.
    Primary source for positive controls — always prefer this over guessing.
    """
    from src.agent.tools.chembl import chembl_bioactivity as _fn
    return await _fn(
        chembl_target_id=chembl_target_id,
        activity_type=activity_type,
        max_activity_nm=max_activity_nm,
        max_results=max_results,
    )


@tool
async def chembl_compound_detail(chembl_id: str) -> dict:
    """Fetch full compound record from ChEMBL including verified SMILES and drug-like properties."""
    from src.agent.tools.chembl import chembl_compound_detail as _fn
    return await _fn(chembl_id=chembl_id)


# ---------------------------------------------------------------------------
# UniProt tools
# ---------------------------------------------------------------------------

@tool
async def uniprot_search(
    query: str,
    reviewed: bool = True,
    max_results: int = 5,
) -> dict:
    """Search UniProt for proteins by name and organism.

    Returns UniProt accession IDs and basic annotation.
    Use this first to get the uniprot_id for detailed lookups.
    """
    from src.agent.tools.uniprot import uniprot_search as _fn
    return await _fn(query=query, reviewed=reviewed, max_results=max_results)


@tool
async def uniprot_entry_detail(uniprot_id: str) -> dict:
    """Fetch detailed UniProt record: function, subcellular location, essentiality phenotype, GO terms.

    Use after uniprot_search to get the accession ID.
    """
    from src.agent.tools.uniprot import uniprot_entry_detail as _fn
    return await _fn(uniprot_id=uniprot_id)


# ---------------------------------------------------------------------------
# PDB tools
# ---------------------------------------------------------------------------

@tool
async def pdb_structure_search(
    uniprot_id: str,
    has_ligand: bool = True,
    max_resolution_angstrom: float = 2.5,
) -> dict:
    """Search RCSB PDB for experimental structures of a protein by UniProt ID.

    Returns PDB IDs sorted by resolution.
    Filter has_ligand=true to find structures with co-crystallized ligands (ideal for docking).
    """
    from src.agent.tools.pdb import pdb_structure_search as _fn
    return await _fn(
        uniprot_id=uniprot_id,
        has_ligand=has_ligand,
        max_resolution_angstrom=max_resolution_angstrom,
    )


@tool
async def pdb_binding_site_info(pdb_id: str) -> dict:
    """Fetch binding site residues and co-crystallized ligand data for a PDB structure.

    Essential for pharmacophore design and docking setup.
    """
    from src.agent.tools.pdb import pdb_binding_site_info as _fn
    return await _fn(pdb_id=pdb_id)


# ---------------------------------------------------------------------------
# RDKit tools (local, no network)
# ---------------------------------------------------------------------------

@tool
def validate_smiles(smiles: str) -> dict:
    """Validate a SMILES string with RDKit and compute Lipinski properties.

    Always call this before reporting any SMILES to the user to confirm it is chemically valid.
    """
    from src.agent.tools.rdkit_tools import validate_smiles as _fn
    return _fn(smiles)


@tool
def calculate_molecular_properties(smiles_list: List[str]) -> dict:
    """Batch compute Lipinski + shape properties (MW, logP, HBD, HBA, TPSA) for a list of SMILES."""
    from src.agent.tools.rdkit_tools import calculate_molecular_properties as _fn
    return _fn(smiles_list)


@tool
def screen_pains(smiles_list: List[str]) -> dict:
    """Apply RDKit PAINS filters (A, B, C) to a list of SMILES.

    Returns is_pains flag and alert names.
    Always apply before recommending compounds for purchase.
    """
    from src.agent.tools.rdkit_tools import screen_pains as _fn
    return _fn(smiles_list)


@tool
def compute_murcko_scaffolds(smiles_list: List[str]) -> dict:
    """Cluster compounds by Murcko scaffold to identify chemotype diversity.

    Returns scaffold clusters sorted by size.
    """
    from src.agent.tools.rdkit_tools import compute_murcko_scaffolds as _fn
    return _fn(smiles_list)


@tool
def generate_decoys(
    positive_smiles_list: List[str],
    num_decoys_per_compound: int = 3,
    mw_tolerance: float = 25.0,
    logp_tolerance: float = 1.0,
) -> dict:
    """Generate DUD-E-style property-matched decoy specifications for positive controls.

    Returns property ranges and instructions for fetching low-similarity decoys via pubchem_similarity_search.
    """
    from src.agent.tools.rdkit_tools import generate_decoys as _fn
    return _fn(
        positive_smiles_list=positive_smiles_list,
        num_decoys_per_compound=num_decoys_per_compound,
        mw_tolerance=mw_tolerance,
        logp_tolerance=logp_tolerance,
    )


# ---------------------------------------------------------------------------
# Tool subsets per sub-agent
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    pubchem_compound_lookup,
    pubchem_bioactivity_search,
    pubchem_similarity_search,
    chembl_target_search,
    chembl_bioactivity,
    chembl_compound_detail,
    uniprot_search,
    uniprot_entry_detail,
    pdb_structure_search,
    pdb_binding_site_info,
    validate_smiles,
    calculate_molecular_properties,
    screen_pains,
    compute_murcko_scaffolds,
    generate_decoys,
]

TARGET_EVALUATOR_TOOLS = [
    uniprot_search,
    uniprot_entry_detail,
    pdb_structure_search,
    validate_smiles,
]

CONTROLS_GENERATOR_TOOLS = [
    chembl_target_search,
    chembl_bioactivity,
    chembl_compound_detail,
    pubchem_compound_lookup,
    pubchem_similarity_search,
    validate_smiles,
    screen_pains,
    generate_decoys,
]

SCREENING_DESIGNER_TOOLS = [
    pdb_binding_site_info,
    validate_smiles,
    calculate_molecular_properties,
    screen_pains,
]

HITS_ANALYZER_TOOLS = [
    pubchem_compound_lookup,
    validate_smiles,
    calculate_molecular_properties,
    screen_pains,
    compute_murcko_scaffolds,
]
