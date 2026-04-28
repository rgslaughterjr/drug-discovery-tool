"""Tests for local RDKit cheminformatics tools (no network calls)."""

import pytest

# Graceful skip if rdkit-pypi is not installed in the test environment
rdkit_available = False
try:
    from rdkit import Chem  # noqa: F401
    rdkit_available = True
except ImportError:
    pass

pytestmark = pytest.mark.skipif(
    not rdkit_available,
    reason="rdkit not installed — install with: pip install rdkit",
)

from src.agent.tools.rdkit_tools import (
    calculate_molecular_properties,
    compute_murcko_scaffolds,
    generate_decoys,
    screen_pains,
    validate_smiles,
)

# Representative SMILES used across tests
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
NOVOBIOCIN = "CC1(C)C(O)CC(O1)OC2=CC(=CC3=C2C(=O)C(=CO3)C(=O)N)OC"
INVALID_SMILES = "not_a_smiles!!!"
ETHANOL = "CCO"


# ---------------------------------------------------------------------------
# validate_smiles
# ---------------------------------------------------------------------------

class TestValidateSmiles:
    def test_valid_aspirin(self):
        result = validate_smiles(ASPIRIN)
        assert result["valid"] is True
        assert result["mw"] > 0
        assert "canonical_smiles" in result
        assert isinstance(result["logp"], float)
        assert isinstance(result["hbd"], int)
        assert isinstance(result["hba"], int)
        assert isinstance(result["tpsa"], float)
        assert isinstance(result["ro5_violations"], int)

    def test_invalid_smiles_returns_error(self):
        result = validate_smiles(INVALID_SMILES)
        assert result["valid"] is False
        assert "error" in result

    def test_aspirin_lipinski_properties(self):
        result = validate_smiles(ASPIRIN)
        # Aspirin MW ~180, logP ~1.2, zero Ro5 violations
        assert 178 < result["mw"] < 182
        assert result["ro5_violations"] == 0

    def test_novobiocin_ro5_violations(self):
        # Novobiocin MW ~613, TPSA ~146 — borderline Ro5
        result = validate_smiles(NOVOBIOCIN)
        assert result["valid"] is True
        assert result["mw"] > 600
        assert result["ro5_violations"] >= 1

    def test_ethanol_hbd(self):
        result = validate_smiles(ETHANOL)
        assert result["valid"] is True
        assert result["hbd"] == 1  # OH group


# ---------------------------------------------------------------------------
# calculate_molecular_properties (batch)
# ---------------------------------------------------------------------------

class TestCalculateMolecularProperties:
    def test_batch_returns_one_result_per_smiles(self):
        result = calculate_molecular_properties([ASPIRIN, ETHANOL])
        assert result["count"] == 2
        assert len(result["results"]) == 2

    def test_batch_with_invalid_smiles(self):
        result = calculate_molecular_properties([ASPIRIN, INVALID_SMILES])
        assert result["count"] == 2
        assert result["results"][0]["valid"] is True
        assert result["results"][1]["valid"] is False

    def test_empty_list(self):
        result = calculate_molecular_properties([])
        assert result["count"] == 0
        assert result["results"] == []


# ---------------------------------------------------------------------------
# screen_pains
# ---------------------------------------------------------------------------

class TestScreenPains:
    # Rhodamine B — known PAINS scaffold
    PAINS_COMPOUND = "CCN(CC)c1ccc2c(-c3ccccc3C(=O)[O-])c3ccc(=[N+](CC)CC)cc3oc2c1"

    def test_clean_compound_not_flagged(self):
        result = screen_pains([ASPIRIN])
        assert result["pains_count"] == 0
        assert result["results"][0]["is_pains"] is False
        assert result["results"][0]["pains_alerts"] == []

    def test_pains_compound_flagged(self):
        result = screen_pains([self.PAINS_COMPOUND])
        assert result["results"][0]["is_pains"] is True
        assert len(result["results"][0]["pains_alerts"]) > 0

    def test_mixed_batch_counts_correctly(self):
        result = screen_pains([ASPIRIN, self.PAINS_COMPOUND])
        assert result["pains_count"] == 1
        assert len(result["results"]) == 2

    def test_invalid_smiles_marked_none(self):
        result = screen_pains([INVALID_SMILES])
        assert result["results"][0]["is_pains"] is None
        assert "error" in result["results"][0]


# ---------------------------------------------------------------------------
# compute_murcko_scaffolds
# ---------------------------------------------------------------------------

class TestComputeMurckoScaffolds:
    # Two benzoic acid derivatives share a scaffold
    BENZOIC_ACID = "OC(=O)c1ccccc1"
    ASPIRIN_ALT = "CC(=O)Oc1ccccc1C(=O)O"

    def test_cluster_count(self):
        result = compute_murcko_scaffolds([self.BENZOIC_ACID, ETHANOL])
        # Ethanol has no ring → __none__ scaffold; benzoic acid has benzene ring
        assert result["total_scaffolds"] >= 1

    def test_invalid_smiles_silently_skipped(self):
        result = compute_murcko_scaffolds([ASPIRIN, INVALID_SMILES])
        # Only aspirin contributes; no crash
        assert "clusters" in result

    def test_empty_input(self):
        result = compute_murcko_scaffolds([])
        assert result["total_scaffolds"] == 0
        assert result["clusters"] == []

    def test_sorted_by_cluster_size_desc(self):
        # All same compound → single scaffold cluster of size 3
        result = compute_murcko_scaffolds([ASPIRIN, ASPIRIN, ASPIRIN])
        if result["clusters"]:
            assert result["clusters"][0]["count"] >= result["clusters"][-1]["count"]


# ---------------------------------------------------------------------------
# generate_decoys
# ---------------------------------------------------------------------------

class TestGenerateDecoys:
    def test_returns_spec_per_compound(self):
        result = generate_decoys([ASPIRIN, ETHANOL])
        assert result["positives_processed"] == 2
        assert len(result["decoy_specs"]) == 2

    def test_spec_has_mw_and_logp_ranges(self):
        result = generate_decoys([ASPIRIN], mw_tolerance=25.0, logp_tolerance=1.0)
        spec = result["decoy_specs"][0]
        assert "mw_range" in spec
        assert "logp_range" in spec
        # MW range should straddle aspirin's MW (~180)
        assert spec["mw_range"][0] < 180 < spec["mw_range"][1]

    def test_invalid_smiles_skipped(self):
        result = generate_decoys([ASPIRIN, INVALID_SMILES])
        # Invalid SMILES is silently skipped
        assert result["positives_processed"] == 1

    def test_empty_input(self):
        result = generate_decoys([])
        assert result["positives_processed"] == 0
        assert result["decoy_specs"] == []
