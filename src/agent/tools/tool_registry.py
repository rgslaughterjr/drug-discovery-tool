"""
Canonical Anthropic tool schema definitions for all 13 tools.
Also provides per-sub-agent subsets and an OpenAI-compatible format converter.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Individual tool definitions (Anthropic input_schema format)
# ---------------------------------------------------------------------------

_PUBCHEM_COMPOUND_LOOKUP = {
    "name": "pubchem_compound_lookup",
    "description": (
        "Look up a compound in PubChem by name, CID, SMILES, or InChIKey. "
        "Returns verified CID, canonical SMILES, and Lipinski properties. "
        "ALWAYS use this before reporting any compound data to confirm it is real."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Compound name, numeric CID (as string), SMILES, or InChIKey",
            },
            "identifier_type": {
                "type": "string",
                "enum": ["name", "cid", "smiles", "inchikey"],
                "description": "Type of the identifier",
            },
        },
        "required": ["identifier", "identifier_type"],
    },
}

_PUBCHEM_BIOACTIVITY_SEARCH = {
    "name": "pubchem_bioactivity_search",
    "description": (
        "Search PubChem for compounds with measured activity against a gene target. "
        "Returns CIDs, names, activity values, and assay IDs. "
        "Use gene symbol (e.g. 'GYRB', 'DHFR') not full protein name."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "target_gene_symbol": {"type": "string", "description": "HGNC gene symbol, e.g. 'GYRB'"},
            "assay_type": {
                "type": "string",
                "enum": ["IC50", "Ki", "Kd", "EC50"],
                "description": "Activity measurement type",
            },
            "activity_cutoff_um": {
                "type": "number",
                "description": "Maximum activity value in µM (e.g. 10.0 = 10µM cutoff)",
            },
            "max_results": {"type": "integer", "description": "Maximum compounds to return", "default": 20},
        },
        "required": ["target_gene_symbol"],
    },
}

_PUBCHEM_SIMILARITY_SEARCH = {
    "name": "pubchem_similarity_search",
    "description": (
        "Find structurally similar compounds by 2D Tanimoto similarity. "
        "Use threshold=85-95 for similar analogs; threshold=30-50 for property-matched decoys "
        "(structurally dissimilar but same MW/logP range)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "smiles": {"type": "string", "description": "Query SMILES string"},
            "threshold": {
                "type": "integer",
                "description": "Tanimoto similarity threshold 0-100",
                "default": 85,
            },
            "max_results": {"type": "integer", "default": 10},
        },
        "required": ["smiles"],
    },
}

_CHEMBL_TARGET_SEARCH = {
    "name": "chembl_target_search",
    "description": (
        "Search ChEMBL for a drug target by name and organism. "
        "Returns ChEMBL target IDs needed for chembl_bioactivity calls. "
        "Always call this first to get the chembl_target_id."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "target_name": {
                "type": "string",
                "description": "Protein name, e.g. 'DNA gyrase subunit B'",
            },
            "organism": {
                "type": "string",
                "description": "Organism name, e.g. 'Staphylococcus aureus'",
            },
        },
        "required": ["target_name"],
    },
}

_CHEMBL_BIOACTIVITY = {
    "name": "chembl_bioactivity",
    "description": (
        "Fetch real bioactivity data (IC50/Ki) for a ChEMBL target. "
        "Returns verified compounds with SMILES, measured affinity, and literature DOIs. "
        "This is the primary source for positive controls — always prefer this over guessing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "chembl_target_id": {
                "type": "string",
                "description": "ChEMBL target ID, e.g. 'CHEMBL2095192'",
            },
            "activity_type": {
                "type": "string",
                "enum": ["IC50", "Ki", "Kd", "EC50", "Inhibition"],
                "default": "IC50",
            },
            "max_activity_nm": {
                "type": "number",
                "description": "Max activity value in nM (e.g. 10000 = 10µM cutoff)",
                "default": 10000.0,
            },
            "max_results": {"type": "integer", "default": 20},
        },
        "required": ["chembl_target_id"],
    },
}

_CHEMBL_COMPOUND_DETAIL = {
    "name": "chembl_compound_detail",
    "description": "Fetch full compound record from ChEMBL including verified SMILES and drug-like properties.",
    "input_schema": {
        "type": "object",
        "properties": {
            "chembl_id": {
                "type": "string",
                "description": "ChEMBL molecule ID, e.g. 'CHEMBL123456'",
            },
        },
        "required": ["chembl_id"],
    },
}

_UNIPROT_SEARCH = {
    "name": "uniprot_search",
    "description": (
        "Search UniProt for proteins by name and organism. "
        "Returns UniProt accession IDs and basic annotation. "
        "Use this first to get the uniprot_id for detailed lookups."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query, e.g. 'GyrB Staphylococcus aureus'",
            },
            "reviewed": {
                "type": "boolean",
                "description": "If true, restrict to Swiss-Prot curated entries",
                "default": True,
            },
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
}

_UNIPROT_ENTRY_DETAIL = {
    "name": "uniprot_entry_detail",
    "description": (
        "Fetch detailed UniProt record: function, subcellular location, essentiality phenotype, GO terms. "
        "Use after uniprot_search to get the accession ID."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "uniprot_id": {
                "type": "string",
                "description": "UniProt accession, e.g. 'P0A749'",
            },
        },
        "required": ["uniprot_id"],
    },
}

_PDB_STRUCTURE_SEARCH = {
    "name": "pdb_structure_search",
    "description": (
        "Search RCSB PDB for experimental structures of a protein by UniProt ID. "
        "Returns PDB IDs sorted by resolution. "
        "Filter has_ligand=true to find structures with co-crystallized ligands (ideal for docking)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "uniprot_id": {
                "type": "string",
                "description": "UniProt accession, e.g. 'P0A749'",
            },
            "has_ligand": {
                "type": "boolean",
                "description": "Filter to structures with bound ligands",
                "default": True,
            },
            "max_resolution_angstrom": {
                "type": "number",
                "description": "Maximum resolution in Ångströms",
                "default": 2.5,
            },
        },
        "required": ["uniprot_id"],
    },
}

_PDB_BINDING_SITE_INFO = {
    "name": "pdb_binding_site_info",
    "description": (
        "Fetch binding site residues and co-crystallized ligand data for a specific PDB structure. "
        "Essential for pharmacophore design and docking setup."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "pdb_id": {
                "type": "string",
                "description": "4-character PDB ID, e.g. '4P8O'",
            },
        },
        "required": ["pdb_id"],
    },
}

_VALIDATE_SMILES = {
    "name": "validate_smiles",
    "description": (
        "Validate a SMILES string with RDKit and compute Lipinski properties. "
        "Always call this before reporting any SMILES to the user to confirm it is chemically valid."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "smiles": {"type": "string", "description": "SMILES string to validate"},
        },
        "required": ["smiles"],
    },
}

_CALCULATE_MOLECULAR_PROPERTIES = {
    "name": "calculate_molecular_properties",
    "description": "Batch compute Lipinski + shape properties (MW, logP, HBD, HBA, TPSA, Fsp3) for a list of SMILES.",
    "input_schema": {
        "type": "object",
        "properties": {
            "smiles_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of SMILES strings",
            },
        },
        "required": ["smiles_list"],
    },
}

_SCREEN_PAINS = {
    "name": "screen_pains",
    "description": (
        "Apply RDKit PAINS filters (A, B, C) to a list of SMILES. "
        "Returns is_pains flag and alert names. "
        "Always apply before recommending compounds for purchase."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "smiles_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of SMILES strings to screen",
            },
        },
        "required": ["smiles_list"],
    },
}

_COMPUTE_MURCKO_SCAFFOLDS = {
    "name": "compute_murcko_scaffolds",
    "description": "Cluster compounds by Murcko scaffold to identify chemotype diversity. Returns scaffold clusters sorted by size.",
    "input_schema": {
        "type": "object",
        "properties": {
            "smiles_list": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["smiles_list"],
    },
}

_GENERATE_DECOYS = {
    "name": "generate_decoys",
    "description": (
        "Generate DUD-E-style property-matched decoy specifications for a list of positive controls. "
        "Returns property ranges and instructions for fetching low-similarity, property-matched decoys "
        "via pubchem_similarity_search."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "positive_smiles_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": "SMILES of confirmed positive controls",
            },
            "num_decoys_per_compound": {"type": "integer", "default": 3},
            "mw_tolerance": {"type": "number", "default": 25.0},
            "logp_tolerance": {"type": "number", "default": 1.0},
        },
        "required": ["positive_smiles_list"],
    },
}

# ---------------------------------------------------------------------------
# Grouped tool sets
# ---------------------------------------------------------------------------

ALL_TOOLS: list[dict] = [
    _PUBCHEM_COMPOUND_LOOKUP,
    _PUBCHEM_BIOACTIVITY_SEARCH,
    _PUBCHEM_SIMILARITY_SEARCH,
    _CHEMBL_TARGET_SEARCH,
    _CHEMBL_BIOACTIVITY,
    _CHEMBL_COMPOUND_DETAIL,
    _UNIPROT_SEARCH,
    _UNIPROT_ENTRY_DETAIL,
    _PDB_STRUCTURE_SEARCH,
    _PDB_BINDING_SITE_INFO,
    _VALIDATE_SMILES,
    _CALCULATE_MOLECULAR_PROPERTIES,
    _SCREEN_PAINS,
    _COMPUTE_MURCKO_SCAFFOLDS,
    _GENERATE_DECOYS,
]

# Per-sub-agent restricted subsets (Nemotron / OpenAI format)
SUB_AGENT_TOOLS: dict[str, list[dict]] = {
    "target_evaluator": [
        _UNIPROT_SEARCH,
        _UNIPROT_ENTRY_DETAIL,
        _PDB_STRUCTURE_SEARCH,
        _VALIDATE_SMILES,
    ],
    "controls_generator": [
        _CHEMBL_TARGET_SEARCH,
        _CHEMBL_BIOACTIVITY,
        _CHEMBL_COMPOUND_DETAIL,
        _PUBCHEM_COMPOUND_LOOKUP,
        _PUBCHEM_SIMILARITY_SEARCH,
        _VALIDATE_SMILES,
        _SCREEN_PAINS,
        _GENERATE_DECOYS,
    ],
    "screening_designer": [
        _PDB_BINDING_SITE_INFO,
        _VALIDATE_SMILES,
        _CALCULATE_MOLECULAR_PROPERTIES,
        _SCREEN_PAINS,
    ],
    "hits_analyzer": [
        _PUBCHEM_COMPOUND_LOOKUP,
        _VALIDATE_SMILES,
        _CALCULATE_MOLECULAR_PROPERTIES,
        _SCREEN_PAINS,
        _COMPUTE_MURCKO_SCAFFOLDS,
    ],
}

# Orchestrator sees all tools plus a synthetic delegation tool
_DELEGATE_TO_SUB_AGENT = {
    "name": "delegate_to_sub_agent",
    "description": (
        "Delegate a complex domain task to a specialized sub-agent. "
        "Sub-agents have access to a focused tool subset and domain-specific prompts. "
        "Use when a workflow step requires multi-tool scientific reasoning. "
        "agent_name options: 'target_evaluator' | 'controls_generator' | "
        "'screening_designer' | 'hits_analyzer'"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "enum": ["target_evaluator", "controls_generator", "screening_designer", "hits_analyzer"],
            },
            "task_description": {
                "type": "string",
                "description": "Plain-language description of what the sub-agent should do",
            },
            "context": {
                "type": "object",
                "description": "Structured context: organism, protein, uniprot_id, pdb_id, chembl_target_id, etc.",
            },
        },
        "required": ["agent_name", "task_description", "context"],
    },
}

ORCHESTRATOR_TOOLS: list[dict] = ALL_TOOLS + [_DELEGATE_TO_SUB_AGENT]


def to_openai_format(tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool schemas to OpenAI function-calling format (for Nemotron)."""
    converted = []
    for t in tools:
        converted.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        })
    return converted
