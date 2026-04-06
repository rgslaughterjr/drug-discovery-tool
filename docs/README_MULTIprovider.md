# Drug Discovery Pipeline: AI-Augmented Virtual Screening

**An AI-assisted computational workflow for discovering novel small-molecule therapeutics against bacterial and protozoan parasitic pathogens.**

This tool implements a four-phase drug discovery pipeline using **any LLM provider**:

1. **Target Evaluation** — Assess a protein as a viable drug target
2. **Validation Controls** — Generate known binders and decoys for docking validation
3. **Screening Preparation** — Design pharmacophore-based ChemBridge Diversity screening
4. **Hit Analysis** — Prioritize and rank virtual screening hits for wet-lab testing

**New: Provider-agnostic architecture** — Use any LLM you have access to (Anthropic, OpenAI, Cohere, Ollama, Together.ai, or custom endpoints).

---

## Quick Start (Anthropic Direct API)

For fastest setup with Anthropic (recommended for UT Austin):

```bash
git clone https://github.com/yourusername/drug-discovery-tool.git
cd drug-discovery-tool
pip install -r requirements.txt

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Run a workflow
jupyter notebook workflows/01_evaluate_target.ipynb
```

When the notebook opens, skip the setup cell (your API key is already configured), and go straight to Step 1.

---

## LLM Provider Setup

### Overview

The pipeline supports **6 major LLM providers** plus **any OpenAI-compatible API**:

| Provider | Cost Model | Best For | Setup Effort |
|----------|-----------|----------|--------------|
| **Anthropic** | Pay-as-you-go (~$0.35/full pipeline) | UT Austin faculty, academic research | 2 min |
| **OpenAI** | Pay-as-you-go (~$1–5/full pipeline) | Users with existing OpenAI account | 2 min |
| **Cohere** | Free tier + paid | Organizations with Cohere partnership | 2 min |
| **AWS Bedrock** | Institutional pricing (potentially discounted) | UT Austin with AWS contract | 5 min |
| **Ollama** | Free (local) | Researchers wanting offline/no-cost LLMs | 10 min |
| **Together.ai** | Pay-as-you-go (~$0.50–2/full pipeline) | Research collaborations, cost-conscious labs | 2 min |
| **Custom** | Varies | Any OpenAI-compatible API | 2 min |

---

## Setup: Choose Your Provider

### Option 1: Anthropic Direct API (Recommended for UT Austin)

**Best for:** Lab owners with institutional compute budgets or NSF/DOE grants.

**Cost:** Pay-as-you-go via [Anthropic Console](https://console.anthropic.com). Approximately **$0.35 per full pipeline execution** (all 4 workflows combined).

**Setup (3 steps):**

1. **Get API key:**
   - Go to https://console.anthropic.com
   - Sign up or log in
   - Navigate to **Settings > API Keys**
   - Generate a new API key and copy it (starts with `sk-ant-`)

2. **Set environment variable (macOS/Linux):**
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"

   # For persistence, add to ~/.bashrc or ~/.zshrc
   echo 'export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"' >> ~/.bashrc
   source ~/.bashrc
   ```

   **Or on Windows (PowerShell):**
   ```powershell
   $env:ANTHROPIC_API_KEY = "sk-ant-YOUR_KEY_HERE"

   # For persistence:
   [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-YOUR_KEY_HERE", "User")
   ```

3. **Verify:**
   ```bash
   python -c "from src import DrugDiscoveryClient; DrugDiscoveryClient(); print('✓ Anthropic configured')"
   ```

4. **Run a notebook:**
   ```bash
   jupyter notebook workflows/01_evaluate_target.ipynb
   ```
   In the notebook, run the setup cell. It will detect your `ANTHROPIC_API_KEY` and skip credential entry.

---

### Option 2: OpenAI (GPT-4, GPT-3.5)

**Best for:** Users with existing OpenAI accounts; familiar with GPT models.

**Cost:** Pay-as-you-go. Approximately **$1–5 per full pipeline** (higher than Anthropic due to token prices).

**Setup:**

1. **Get API key:**
   - Go to https://platform.openai.com/api/keys
   - Create a new API key (starts with `sk-`)
   - Copy it

2. **Set environment variable:**
   ```bash
   export OPENAI_API_KEY="sk-YOUR_KEY_HERE"

   # Persistence:
   echo 'export OPENAI_API_KEY="sk-YOUR_KEY_HERE"' >> ~/.bashrc
   ```

3. **Run a notebook:**
   ```bash
   jupyter notebook workflows/01_evaluate_target.ipynb
   ```
   In the setup cell, select **"2. openai"** when prompted.
   - API Key: Paste your OpenAI key
   - Model: `gpt-4-turbo` (recommended) or `gpt-4` or `gpt-3.5-turbo`

**Note:** For Azure OpenAI, use the same setup but specify `base_url` as your Azure endpoint:
```
https://YOUR_RESOURCE.openai.azure.com/v1
```

---

### Option 3: Cohere

**Best for:** Organizations with Cohere partnerships; researchers exploring diverse providers.

**Cost:** Free tier (1,000 API calls/month) + paid overages (~$0.50–1 per full pipeline).

**Setup:**

1. **Get API key:**
   - Go to https://dashboard.cohere.com/api-keys
   - Create a new API key
   - Copy it

2. **Set environment variable:**
   ```bash
   export COHERE_API_KEY="YOUR_KEY_HERE"
   ```

3. **Run a notebook:**
   ```bash
   jupyter notebook workflows/01_evaluate_target.ipynb
   ```
   In the setup cell, select **"3. cohere"**.
   - API Key: Paste your Cohere key
   - Model: `command-r-plus` (recommended) or `command-r` or `command-light`

---

### Option 4: Ollama (Local LLMs, Free & Offline)

**Best for:** Researchers wanting zero API costs, offline capability, or experimenting with open-source LLMs.

**Cost:** Free (runs locally on your machine).

**Models available:** Llama 2, Mistral, Neural Chat, Zephyr, etc.

**Setup (5 steps):**

1. **Install Ollama:**
   - Go to https://ollama.ai
   - Download and install for macOS, Linux, or Windows

2. **Start Ollama server:**
   ```bash
   ollama serve
   ```
   (Runs on http://localhost:11434 by default)

3. **Download a model (in a new terminal):**
   ```bash
   ollama pull llama2
   # Or try: mistral, neural-chat, zephyr, or another model
   ```

4. **Verify Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```
   You should see a list of downloaded models.

5. **Run a notebook:**
   ```bash
   jupyter notebook workflows/01_evaluate_target.ipynb
   ```
   In the setup cell, select **"5. ollama"**.
   - API Key: Leave blank (Ollama requires no key)
   - Model: `llama2` (or whichever you downloaded)
   - Endpoint: `http://localhost:11434/v1` (default)

**Troubleshooting:**
- If Ollama doesn't respond, ensure the server is running: `ollama serve`
- Verify connectivity: `curl http://localhost:11434/api/tags`
- For slower machines, responses may take 30–60 seconds

---

### Option 5: AWS Bedrock (Institutional)

**Best for:** UT Austin with institutional AWS account; organizations needing audit trails (CloudTrail).

**Cost:** Institutional pricing (potentially lower than direct API).

**Setup (5 steps):**

1. **Verify AWS credentials:**
   ```bash
   aws sts get-caller-identity
   ```
   If this fails, you don't have AWS configured. Skip this option.

2. **Enable Bedrock model access (one-time):**
   - Go to https://console.aws.amazon.com/bedrock/
   - Select your region (e.g., `us-west-2`)
   - Go to **Model access** > **Manage model access**
   - Enable **Anthropic Claude 3.5 Sonnet**
   - Click **Save changes**

3. **Set environment variables:**
   ```bash
   export DISCOVERY_PROVIDER="bedrock"
   export AWS_REGION="us-west-2"
   # AWS credentials auto-loaded from ~/.aws/credentials
   ```

4. **Run a notebook:**
   ```bash
   jupyter notebook workflows/01_evaluate_target.ipynb
   ```
   In the setup cell, select **"4. bedrock"**.
   - API Key: Leave blank (uses AWS credentials)
   - Model: `claude-3-5-sonnet-20241022` (default)

5. **Monitor costs:**
   - Go to AWS Console > **Bedrock** > **Usage** to track spending

---

### Option 6: Together.ai

**Best for:** Researchers collaborating with Together.ai; cost-conscious labs.

**Cost:** Pay-as-you-go (~$0.50–2 per full pipeline).

**Setup:**

1. **Get API key:**
   - Go to https://www.together.ai/
   - Sign up or log in
   - Generate an API key in **Account > API Keys**

2. **Set environment variable:**
   ```bash
   export TOGETHER_API_KEY="YOUR_KEY_HERE"
   ```

3. **Run a notebook:**
   ```bash
   jupyter notebook workflows/01_evaluate_target.ipynb
   ```
   In the setup cell, select **"6. together"**.
   - API Key: Paste your Together key
   - Model: `meta-llama/Llama-2-7b-chat-hf` (recommended) or another open-source model

---

### Option 7: Custom OpenAI-Compatible API

**For:** Any other OpenAI-compatible API (local APIs, vLLM, text-generation-webui, etc.).

**Setup:**

1. **Set up your custom endpoint** (ensure it's running and accessible)

2. **Run a notebook:**
   ```bash
   jupyter notebook workflows/01_evaluate_target.ipynb
   ```
   In the setup cell, select a provider or enter a custom name.
   - API Key: Your API key (if required)
   - Model: Your model name
   - Base URL: `https://your-custom-api.com/v1` or similar

---

## Installation & Dependencies

### Core Setup

```bash
# Clone repository
git clone https://github.com/yourusername/drug-discovery-tool.git
cd drug-discovery-tool

# Install core + recommended (Anthropic)
pip install -r requirements.txt
```

### Install Only What You Need

Each provider requires specific packages. Install only what you'll use:

```bash
# Anthropic only
pip install anthropic python-dotenv jupyter ipython

# OpenAI only
pip install openai python-dotenv jupyter ipython

# Cohere only
pip install cohere python-dotenv jupyter ipython

# Ollama only (uses openai package)
pip install openai python-dotenv jupyter ipython

# Together.ai only (uses openai package)
pip install openai python-dotenv jupyter ipython

# AWS Bedrock only
pip install boto3 python-dotenv jupyter ipython

# All providers
pip install -r requirements.txt
```

---

## Running Workflows

### Interactive Setup (Easiest)

Simply run a notebook and the setup cell will guide you:

```bash
jupyter notebook workflows/01_evaluate_target.ipynb
```

The setup cell will:
1. List available providers
2. Prompt you to select one
3. Ask for API key (if needed)
4. Ask for model name (with defaults)
5. Test the connection
6. Initialize the client for the rest of the notebook

### Programmatic Setup (For Scripts)

```python
from src import DrugDiscoveryClient, APIConfig

# Anthropic
config = APIConfig(
    provider="anthropic",
    api_key="sk-ant-...",
    model="claude-3-5-sonnet-20241022"
)

# OpenAI
config = APIConfig(
    provider="openai",
    api_key="sk-...",
    model="gpt-4-turbo"
)

# Ollama (local)
config = APIConfig(
    provider="ollama",
    model="llama2",
    base_url="http://localhost:11434/v1"
)

# Initialize client
client = DrugDiscoveryClient(config=config)

# Use it
result = client.evaluate_target(
    organism="Staphylococcus aureus",
    protein_name="DNA gyrase subunit B"
)
print(result["response"])
```

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
- GO/NO-GO recommendation
- Suggested alternatives if NO-GO

**Runtime:** ~60 seconds (varies by provider)

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
- Literature references

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
Docking software: Autodock Vina
```

**Output:**
- Ranked pharmacophore features
- Physicochemical filter cutoffs
- PAINS exclusion rules
- ZINC20 query with SMARTS filters
- Estimated library size after filtering
- Hit prioritization strategy

**Runtime:** ~120 seconds

---

### Workflow 4: Analyze Virtual Screening Hits

**File:** `workflows/04_analyze_hits.ipynb`

**Input:**
```
Protein: S. aureus GyrB
Compounds screened: 180,000
Docking score distribution
Positive control affinity values (optional)
```

**Output:**
- Score cutoff determination
- Murcko scaffold clustering
- PAINS re-filtering results
- Selectivity cross-check strategy
- Prioritized purchase list (top 10–20 compounds)
- Visual inspection checklist

**Runtime:** ~90 seconds

---

## Cost Comparison

**Typical cost per full pipeline execution (all 4 workflows):**

| Provider | Est. Cost | Notes |
|----------|-----------|-------|
| Anthropic | $0.35 | Recommended; lowest cost |
| OpenAI (GPT-4) | $1.50 | Higher token prices; good quality |
| OpenAI (GPT-3.5) | $0.50 | Cheaper; slightly lower quality |
| Cohere | $0.50 | Free tier available; variable quality |
| AWS Bedrock | $0.40 | Institutional pricing (if applicable) |
| Together.ai | $0.80 | Competitive pricing |
| Ollama | $0.00 | Free; runs locally |

**Annual estimate (50 target evaluations):**
- Anthropic: ~$17.50 per year
- OpenAI (GPT-4): ~$75 per year
- Ollama (free): $0

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

### "API key not set"

```bash
# Verify key exists
echo $ANTHROPIC_API_KEY  # macOS/Linux
echo %ANTHROPIC_API_KEY%  # Windows

# If empty, set it
export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY"
```

### "Invalid API key"

- **Anthropic:** Key must start with `sk-ant-`. Check the Anthropic Console.
- **OpenAI:** Key must start with `sk-`. Check OpenAI Platform.
- **Cohere:** Verify at https://dashboard.cohere.com/api-keys.
- **Together.ai:** Verify at https://www.together.ai/.

### "Connection refused" (Ollama)

- Ensure Ollama is running: `ollama serve`
- Check Ollama is accessible: `curl http://localhost:11434/api/tags`
- If using custom endpoint, verify the URL is correct

### "Model not found"

- **Ollama:** Download the model first: `ollama pull llama2`
- **Other providers:** Verify model name is correct and available in your account

### Slow responses

- First call to any provider may take longer (initialization/caching)
- Ollama on slower hardware may take 30–60 seconds
- Check internet connection and API rate limits

---

## File Structure

```
drug-discovery-tool/
├── src/
│   ├── __init__.py              # Package exports
│   ├── api_client.py            # Unified LLM client (provider-agnostic)
│   └── config.py                # Configuration utilities
├── prompts/
│   ├── evaluate_target_system.txt
│   ├── get_controls_system.txt
│   ├── chembridge_prep_system.txt
│   └── hit_analysis_system.txt
├── workflows/
│   ├── 01_evaluate_target.ipynb
│   ├── 02_generate_controls.ipynb
│   ├── 03_prepare_screening.ipynb
│   └── 04_analyze_hits.ipynb
├── examples/
│   ├── gyrb_evaluation.json
│   ├── gyrb_controls.json
│   └── pfddhfr_screening_brief.json
├── requirements.txt
├── README.md                    # This file
└── .env.example                 # Environment variable template
```

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
  note={LLM-agnostic computational drug discovery framework}
}
```

---

## License

MIT License — See LICENSE file for details.

---

## Contact

For questions or support:
- **Technical issues:** [GitHub Issues]
- **Anthropic (if using Direct API):** support@anthropic.com
- **OpenAI (if using GPT models):** support@openai.com

---

## Acknowledgments

Built for the [Lab Name] at The University of Texas at Austin.

Designed for advanced undergraduate researchers performing real drug discovery against infectious disease targets. Provider-agnostic architecture enables any researcher to use their preferred LLM platform.
