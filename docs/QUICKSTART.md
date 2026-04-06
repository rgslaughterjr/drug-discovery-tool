# Drug Discovery Tool - Quick Start

## Download Options

You have two archive formats:

- **drug-discovery-tool.tar.gz** (17 KB) — Smaller, Linux/Mac
- **drug-discovery-tool.zip** (25 KB) — Windows-friendly

Pick whichever your OS prefers.

---

## Extract the Archive

### On Mac/Linux:
```bash
tar -xzf drug-discovery-tool.tar.gz
cd drug-discovery-tool
```

### On Windows:
Right-click the `.zip` file → Extract All → Enter folder

---

## What's Inside

```
drug-discovery-tool/
├── README.md                    ← Lab owner setup guide (read this first)
├── DEVELOPMENT.md               ← Your development/iteration guide
├── requirements.txt             ← Python dependencies
├── .env.example                 ← Configuration template
├── .gitignore
│
├── src/
│   ├── api_client.py           ← Core API client (supports Anthropic + Bedrock)
│   ├── config.py               ← Configuration loader
│   └── __init__.py
│
├── prompts/                     ← System prompts (currently empty)
│   └── (Ready for you to fill with skill logic)
│
├── workflows/                   ← Four interactive Jupyter notebooks
│   ├── 01_evaluate_target.ipynb
│   ├── 02_generate_controls.ipynb
│   ├── 03_prepare_screening.ipynb
│   └── 04_analyze_hits.ipynb
│
└── examples/
    └── example_gyrb_evaluation.json  ← Reference output
```

---

## Quick Test (5 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Run one notebook
jupyter notebook workflows/01_evaluate_target.ipynb

# 4. Input a test target (e.g., "Staphylococcus aureus / GyrB")
# 5. Hit "Run All" and watch it work
```

Cost: ~$0.05

---

## What Each Workflow Does

| Notebook | Input | Output | Time |
|----------|-------|--------|------|
| 01_evaluate_target | Organism + protein name | GO/NO-GO + criteria assessment | 60s |
| 02_generate_controls | Organism + protein + PDB ID | 10 positives + 10 negatives with SMILES | 90s |
| 03_prepare_screening | Organism + protein + PDB ID + mechanism | ZINC queries, filters, pharmacophore | 120s |
| 04_analyze_hits | Protein + docking scores | Ranked purchase list + hit checklist | 90s |

---

## Next Steps

1. **Read `README.md`** for full setup and API reference
2. **Read `DEVELOPMENT.md`** for guidance on iterating in this Claude project
3. **Test notebooks** with your API key (cost: ~$0.35 for full pipeline)
4. **Extract skill logic** from your 7 Claude skills into `prompts/` folder
5. **Build reference outputs** for 3–5 real targets
6. **When satisfied**, push to GitHub for lab owner

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'anthropic'"**
```bash
pip install -r requirements.txt
```

**"ANTHROPIC_API_KEY not set"**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Notebook won't run**
- Make sure you're in the `drug-discovery-tool/` directory
- Run: `jupyter notebook workflows/01_evaluate_target.ipynb`

---

## Support

See README.md or DEVELOPMENT.md for detailed documentation.

Questions? Ask in this Claude project.
