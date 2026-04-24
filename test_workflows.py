"""
Test script: Verify all 4 workflows work standalone (outside notebooks).
Run: python test_workflows.py
"""

import sys
from src.workflows import (
    evaluate_target_workflow,
    get_controls_workflow,
    prep_screening_workflow,
    analyze_hits_workflow,
)

print("=" * 70)
print("TESTING REFACTORED WORKFLOWS (Python modules, not notebooks)")
print("=" * 70)

# Test 1: Evaluate Target
print("\n✓ Test 1: Evaluate Target")
print("-" * 70)
try:
    result = evaluate_target_workflow(
        organism="Staphylococcus aureus",
        protein_name="DNA gyrase subunit B",
        protein_id="GyrB",
    )
    assert result["status"] == "success"
    assert result["task"] == "evaluate_target"
    assert result["organism"] == "Staphylococcus aureus"
    assert "response" in result
    print(f"  Status: {result['status']}")
    print(f"  Task: {result['task']}")
    print(f"  Response length: {len(result['response'])} chars")
    print("  ✅ PASSED")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

# Test 2: Get Controls
print("\n✓ Test 2: Get Controls")
print("-" * 70)
try:
    result = get_controls_workflow(
        organism="Staphylococcus aureus",
        protein_name="DNA gyrase subunit B",
        pdb_id="4P8O",
    )
    assert result["status"] == "success"
    assert result["task"] == "get_controls"
    assert result["pdb_id"] == "4P8O"
    assert "response" in result
    print(f"  Status: {result['status']}")
    print(f"  Task: {result['task']}")
    print(f"  Response length: {len(result['response'])} chars")
    print("  ✅ PASSED")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

# Test 3: Prep Screening
print("\n✓ Test 3: Prep Screening")
print("-" * 70)
try:
    result = prep_screening_workflow(
        organism="Plasmodium falciparum",
        protein_name="Dihydrofolate reductase",
        pdb_id="1J3I",
        mechanism="Competitive NADPH inhibition",
        docking_software="Autodock Vina",
    )
    assert result["status"] == "success"
    assert result["task"] == "prep_screening"
    assert result["mechanism"] == "Competitive NADPH inhibition"
    assert "response" in result
    print(f"  Status: {result['status']}")
    print(f"  Task: {result['task']}")
    print(f"  Response length: {len(result['response'])} chars")
    print("  ✅ PASSED")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

# Test 4: Analyze Hits
print("\n✓ Test 4: Analyze Hits")
print("-" * 70)
try:
    result = analyze_hits_workflow(
        protein_name="S. aureus GyrB",
        num_compounds=180000,
        docking_scores_summary="Mean: -8.2, SD: 1.1, Range: [-12.5, -4.3]",
        positive_controls_affinity="SPR720: 0.063 µM, Clorobiocin: 0.024 µM",
    )
    assert result["status"] == "success"
    assert result["task"] == "analyze_hits"
    assert result["num_screened"] == 180000
    assert "response" in result
    print(f"  Status: {result['status']}")
    print(f"  Task: {result['task']}")
    print(f"  Response length: {len(result['response'])} chars")
    print("  ✅ PASSED")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("ALL TESTS PASSED ✅")
print("Workflows are ready for web API integration")
print("=" * 70)
