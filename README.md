# Drug Discovery Pipeline: AI-Augmented Virtual Screening

**An AI-assisted computational workflow for discovering novel small-molecule therapeutics against bacterial and protozoan parasitic pathogens.**

This tool implements a four-phase drug discovery pipeline:

1. **Target Evaluation** — Assess a protein as a viable drug target
2. **Validation Controls** — Generate known binders and decoys for docking validation
3. **Screening Preparation** — Design pharmacophore-based ChemBridge Diversity screening
4. **Hit Analysis** — Prioritize and rank virtual screening hits for wet-lab testing

---

## Quick Start (Anthropic Direct API)

**For development or academic use with your own API key:**

```bash
# Clone and setup
git clone https://github.com/yourusername/drug-discovery-tool.git
cd drug-discovery-tool
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run a workflow
jupyter notebook workflows/01_evaluate_target.ipynb
```

---

## Setup: Two Options

### Option A: Anthropic Direct API (Recommended for UT Austin faculty)

**Best for:** Lab owners with institutional compute budgets or NSF/DOE grants.

**Cost:** Pay-as-you-go via [Anthropic Console](https://console.anthropic.com). Approximately **$0.50–$2.00 per workflow execution** depending on target complexity.

**Setup (3 steps):**

1. **Get API key:**
   - Create account at https://console.anthropic.com
   - Generate API key in Settings > API Keys
   - Copy the `sk-ant-...` key

2. **Set environment variable:**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
   
   Or add to `~/.bashrc` / `~/.zshrc` for persistence:
   ```bash
   echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Verify:**
   ```bash
   python -c "from src import DrugDiscoveryClient; print('✓ API configured')"
   ```

---

### Option B: AWS Bedrock (If UT Austin has institutional account)

**Best for:** Institutions with existing AWS contracts or CloudTrail audit requirements.

**Cost:** Potentially discounted if UT Austin has institutional pricing agreement with AWS.

**Setup (5 steps):**

1. **Verify AWS access:**
   ```bash
   aws sts get-caller-identity
   ```
   If this fails, you don't have AWS credentials configured. Skip this option.

2. **Enable Bedrock model access** (one-time in AWS Console):
   - Go to https://console.aws.amazon.com/bedrock/
   - Regions > us-west-2 (or your region)
   - Model access > Enable "Claude 3.5 Sonnet"

3. **Configure environment:**
   ```bash
   export DISCOVERY_PROVIDER="bedrock"
   export AWS_REGION="us-west-2"
   # AWS credentials auto-loaded from ~/.aws/credentials
   ```

4. **Verify:**
   ```bash
   python -c "from src import DrugDiscoveryClient; print('✓ Bedrock configured')"
   ```

5. **Check billing** in AWS Console > Bedrock > Usage.

---

### Option C: UT Austin Institutional Partnership (Contact Anthropic directly)

**Best for:** Long-term, high-volume research collaborations.

**Action:**
- Contact Anthropic Research Partnerships: partnerships@anthropic.com
- Reference: "Academic research partnership inquiry - UT Austin drug discovery lab"
- Mention: Expected annual API usage, research scope, publication plans

Anthropic may offer discounted research credits or direct partnership terms.

---

## Development vs. Deployment

### **For Your Iterations (In This Claude Project)**

Use your own Anthropic API key. You're in development mode:

```bash
# You iterate with:
export ANTHROPIC_API_KEY="sk-ant-..."
python -m jupyter lab  # or notebook
# Each execution is your cost
```

### **For Lab Owner Deployment**

He uses his own key (via BYOK pattern):

```bash
# Lab owner sets THEIR key:
export ANTHROPIC_API_KEY="sk-ant-..." # His key, his cost

# Or (for Bedrock):
export DISCOVERY_PROVIDER="bedrock"   # Uses his AWS account

# Runs notebooks:
jupyter notebook workflows/
```

**Key principle:** Each user's API key = each user's billing. No bill pass-through.

---

## Workflows

### Workflow 1: Evaluate a Target Protein

**File:** `workflows/01_evaluate_target.ipynb`

**Input:**
```
Organism: Staphylococcus aureus
Protein: DNA gyrase subunit B (GyrB)
Optional: UniProt ID or PDB code
```

**Output:**
- Five-criterion assessment (essentiality, structure, assay, purification, novelty)
- GO/NO-GO recommendation with justification
- Suggested alternatives if NO-GO

**Runtime:** ~60 seconds

---

### Workflow 2: Generate Validation Controls

**File:** `workflows/02_generate_controls.ipynb`

**Input:**
```
Organism: Staphylococcus aureus
Protein: DNA gyrase subunit B
PDB ID: 4P8O
```

**Output:**
- 10 positive controls (known binders with IC₅₀/K_i data)
- 10 property-matched negative controls (DUD-E decoys)
- SMILES strings, PubChem CIDs, molecular properties
- Literature references for all compounds

**Runtime:** ~90 seconds

---

### Workflow 3: Prepare Screening Campaign

**File:** `workflows/03_prepare_screening.ipynb`

**Input:**
```
Organism: Plasmodium falciparum
Protein: Dihydrofolate reductase (DHFR)
PDB ID: 1J3I
Mechanism: Competitive NADPH inhibition
Docking software: Autodock Vina (or DOCK6 / Glide / rDock)
```

**Output:**
- Ranked pharmacophore features
- Physicochemical filter cutoffs (MW, LogP, TPSA, HBD/HBA)
- PAINS exclusion rules
- ZINC20 query with SMARTS filters
- Estimated library size after filtering
- Post-screening hit prioritization strategy

**Runtime:** ~120 seconds

---

### Workflow 4: Analyze Virtual Screening Hits

**File:** `workflows/04_analyze_hits.ipynb`

**Input:**
```
Protein: S. aureus GyrB
Compounds screened: 180,000
Docking score distribution summary
Positive control affinity values (optional)
```

**Output:**
- Score cutoff determination (anchored to positive controls)
- Murcko scaffold clustering
- PAINS re-filtering results
- Selectivity cross-check strategy
- Prioritized purchase list (top 10–20 compounds)
- Visual inspection checklist for medicinal chemist

**Runtime:** ~90 seconds

---

## File Structure

```
drug-discovery-tool/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── api_client.py            # Unified API client (Anthropic + Bedrock)
│   └── config.py                # Configuration loader
├── prompts/
│   ├── evaluate_target_system.txt      # System prompt for target evaluation
│   ├── get_controls_system.txt         # System prompt for controls
│   ├── chembridge_prep_system.txt      # System prompt for screening prep
│   └── hit_analysis_system.txt         # System prompt for hit analysis
├── workflows/
│   ├── 01_evaluate_target.ipynb        # Interactive Jupyter notebook
│   ├── 02_generate_controls.ipynb
│   ├── 03_prepare_screening.ipynb
│   └── 04_analyze_hits.ipynb
├── examples/
│   ├── gyrb_evaluation.json            # Example outputs
│   ├── gyrb_controls.json
│   ├── pfddhfr_screening_brief.json
│   └── gyrb_hits_analysis.json
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── .env.example                 # Environment variable template
```

---

## Cost Estimation

**Anthropic Direct API pricing (as of 2025):**
- Input: $3.00 / 1M tokens
- Output: $15.00 / 1M tokens

**Per-workflow cost:**
| Workflow | Approx. tokens | Est. cost |
|----------|----------------|-----------|
| Evaluate target | 3,000 | $0.05 |
| Generate controls | 5,000 | $0.10 |
| Prepare screening | 6,000 | $0.12 |
| Analyze hits | 4,000 | $0.08 |
| **Full pipeline** | **18,000** | **$0.35** |

**Annual cost estimate (50 target evaluations):**
- ~900 tokens × 50 evaluations = ~45K tokens
- Cost: ~$0.13–$0.25/month

---

## API Reference

### Instantiate Client

```python
from src import DrugDiscoveryClient, APIConfig

# With explicit config
config = APIConfig(
    provider="anthropic",
    api_key="sk-ant-...",
    model="claude-3-5-sonnet-20241022"
)
client = DrugDiscoveryClient(config=config)

# Or auto-load from environment
client = DrugDiscoveryClient()
```

### Evaluate Target

```python
result = client.evaluate_target(
    organism="Staphylococcus aureus",
    protein_name="DNA gyrase subunit B",
    protein_id="GyrB"  # optional
)
print(result["response"])
```

### Generate Controls

```python
result = client.get_controls(
    organism="Staphylococcus aureus",
    protein_name="DNA gyrase subunit B",
    pdb_id="4P8O"
)
print(result["response"])
```

### Prepare Screening

```python
result = client.prep_screening(
    organism="Plasmodium falciparum",
    protein_name="Dihydrofolate reductase",
    pdb_id="1J3I",
    mechanism="Competitive NADPH inhibition",
    docking_software="Autodock Vina"
)
print(result["response"])
```

### Analyze Hits

```python
result = client.analyze_hits(
    protein_name="S. aureus GyrB",
    num_compounds=180000,
    docking_scores_summary="Mean: -8.2, SD: 1.1, Range: [-12.5, -4.3]",
    positive_controls_affinity="SPR720: 0.063 µM, Clorobiocin: 0.024 µM"
)
print(result["response"])
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

```bash
# Verify key is exported
echo $ANTHROPIC_API_KEY

# If empty, set it
export ANTHROPIC_API_KEY="sk-ant-..."

# For persistence, add to ~/.bashrc or ~/.zshrc
```

### "AWS credentials not found" (Bedrock mode)

```bash
# Check AWS configuration
aws sts get-caller-identity

# If fails, configure credentials
aws configure

# Or set directly
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
```

### "Model access not enabled" (Bedrock mode)

Go to AWS Console > Bedrock > Model access and enable "Claude 3.5 Sonnet" in your region.

### Slow responses

- First call to Bedrock may take 5–10 seconds (cold start)
- Anthropic Direct API typically responds in 2–5 seconds
- Check internet connection and API quota

---

## Contributing

For improvements, bug reports, or new workflows:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-workflow`
3. Commit changes: `git commit -m "Add [workflow] for [task]"`
4. Push to branch: `git push origin feature/my-workflow`
5. Submit a pull request

---

## Citation

If you use this pipeline in published research, please cite:

```bibtex
@software{drug_discovery_pipeline_2025,
  title={Drug Discovery Pipeline: AI-Augmented Virtual Screening},
  author={[Your Name]},
  year={2025},
  url={https://github.com/yourusername/drug-discovery-tool},
  note={Computational drug discovery framework}
}
```

---

## License

MIT License — See LICENSE file for details.

---

## Contact

For questions or support:
- **PI/Lab Owner:** [Contact]
- **Technical issues:** [GitHub Issues]
- **Anthropic Support:** support@anthropic.com (if using Direct API)

---

## Acknowledgments

Built for the [Lab Name] at The University of Texas at Austin.

Designed for advanced undergraduate researchers performing real drug discovery against infectious disease targets.
