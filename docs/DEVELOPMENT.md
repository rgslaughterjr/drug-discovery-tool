# Development Guide: Iterating Within This Claude Project

This document explains how to iterate and refine the drug discovery tool while you're developing it in this Claude project instance, keeping your API costs isolated and under control.

---

## Development Setup (Your Current Work)

You're building and refining the pipeline with your own Anthropic API key. This is correct.

### Your Development Workflow

```bash
# 1. Set your API key (one time)
export ANTHROPIC_API_KEY="sk-ant-..."

# 2. Install dependencies
pip install -r requirements.txt

# 3. Iterate in Jupyter notebooks
jupyter notebook workflows/

# 4. Each execution against your key is **your cost** (~$0.05–$0.12 per workflow)

# 5. When satisfied with a result, save outputs to examples/
# → These become reference outputs for your lab owner
```

### Cost Control During Development

| Activity | Cost | Frequency |
|----------|------|-----------|
| Test target evaluation | ~$0.05 | 2–3 times while refining |
| Test controls generation | ~$0.10 | 1–2 times while refining |
| Test screening prep | ~$0.12 | 1–2 times while refining |
| Hit analysis test | ~$0.08 | 1–2 times while refining |
| **Total dev cost** | **~$0.70** | **One full pipeline validation** |

---

## What You're Building (Three Layers)

### Layer 1: API Client (BYOK-ready)
**File:** `src/api_client.py`

- Accepts `ANTHROPIC_API_KEY` environment variable
- Also supports AWS Bedrock via `DISCOVERY_PROVIDER` environment variable
- Lab owner will provide their own credentials

```python
# You (development): Uses your key via environment
client = DrugDiscoveryClient()  # Auto-loads ANTHROPIC_API_KEY

# Lab owner (deployment): Uses their key
export ANTHROPIC_API_KEY="sk-ant-..." # His key
client = DrugDiscoveryClient()  # Uses his key
```

### Layer 2: Prompts (Skill Logic)
**Files:** `prompts/*.txt`

- Currently using fallback generic prompts in `api_client.py`
- You can extract full prompt logic from your 7 Claude skills
- These prompts will be the same for both your development and the lab owner's deployment

### Layer 3: Jupyter Notebooks (Interactive Workflows)
**Files:** `workflows/*.ipynb`

- User-facing interfaces (you or lab owner)
- No hardcoded credentials
- Flexible input via notebook cells

---

## Refining the Prompts

As you iterate, you'll want to improve the decision-making logic in the API calls.

### Current State (Fallback Prompts)

The `api_client.py` contains generic fallback prompts. These work but are not optimized.

### Next Step: Extract Your Skill Logic

You have 7 Claude skills with detailed, production-grade decision trees:

1. `drug-target-evaluator` → `prompts/evaluate_target_system.txt`
2. `get-controls` → `prompts/get_controls_system.txt`
3. `chembridge-prep` → `prompts/chembridge_prep_system.txt`
4. Three newer skills for docking, hit analysis, enzyme assays

**To extract and improve:**

1. Read the `.SKILL.md` file for each skill
2. Distill the decision tree into a system prompt
3. Save to `prompts/[task]_system.txt`
4. Update `api_client._load_prompt()` to read from file first:

```python
def _load_prompt(self, task_name: str) -> str:
    """Load system prompt for a task"""
    prompt_dir = os.path.join(
        os.path.dirname(__file__), "..", "prompts"
    )
    prompt_path = os.path.join(prompt_dir, f"{task_name}_system.txt")

    if os.path.exists(prompt_path):
        with open(prompt_path, "r") as f:
            return f.read()
    
    # Fallback to generic if file not found
    return self._get_generic_prompt(task_name)
```

---

## Workflow: Develop → Test → Save → Document

### 1. **Develop a new feature or refine a prompt**

```bash
# Edit the code or prompt logic
# Test in Jupyter
jupyter notebook workflows/01_evaluate_target.ipynb

# Input test case: S. aureus GyrB
# Review output quality
```

### 2. **When satisfied, save example output**

```python
# Inside notebook, after running client.evaluate_target():
output_file = f"../examples/gyrb_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, "w") as f:
    json.dump(result, f, indent=2)
```

This becomes a **reference output** showing the lab owner what quality to expect.

### 3. **Document the decision**

In the notebook or in a `DECISIONS.md`:

```markdown
## Target: S. aureus GyrB

**Why GO?**
- ✓ Essential (CRISPRi confirmed)
- ✓ High-res structure (2.0 Å, PDB 4P8O)
- ✓ Simple assay (ATP/GTP-gated channel, commercial substrates)
- ✓ Purification: His-tag + Ni-NTA (standard)
- ✓ Novel scaffold opportunity (not saturated)

**Key recommendations:**
- Docking structure: 4P8O (ATP-bound, highest resolution)
- Expected positive control IC50: 0.024–0.15 µM
- Screening filters: Fsp3 > 0.25, TPSA 20–130 Å²
```

### 4. **Commit to git**

```bash
git add workflows/
git add examples/gyrb_evaluation_20250331.json
git add DECISIONS.md
git commit -m "Validate GyrB as GO target with full controls + screening brief"
```

---

## Testing Checklist Before Handoff

When you're ready to demo to the lab owner, verify:

- [ ] All four notebooks run without errors (with mock data if needed)
- [ ] Output quality is publication-grade
- [ ] Example outputs are comprehensive (2–3 real targets)
- [ ] README clearly explains BYOK setup
- [ ] .env.example has both Anthropic and Bedrock options
- [ ] No hardcoded credentials anywhere in code
- [ ] Git history is clean and informative

---

## Example Development Session

Here's what a typical iteration looks like:

```bash
# 1. Start development
export ANTHROPIC_API_KEY="sk-ant-..."
jupyter notebook

# 2. Run Workflow 1: Evaluate target
# Input: Staphylococcus aureus / GyrB
# Output: GO recommendation
# Cost: $0.05

# 3. Review result → Good quality
# Save output: examples/gyrb_evaluation.json

# 4. Run Workflow 2: Generate controls
# Input: S. aureus / GyrB / 4P8O
# Output: 10 positives + 10 negatives
# Cost: $0.10

# 5. Review tables → Missing some controls, refine prompt
# Edit: prompts/get_controls_system.txt
# Re-run: $0.10

# 6. Much better → Save: examples/gyrb_controls.json

# 7. Run Workflow 3: Prepare screening
# Input: S. aureus / GyrB / 4P8O / ATP-binding mechanism
# Output: ZINC queries, filters, purchase list
# Cost: $0.12

# 8. Perfect → Save: examples/gyrb_screening.json

# 9. Total development cost: ~$0.37 for a complete pipeline test
```

---

## FAQ: Development-Specific Questions

**Q: If I improve a prompt and test it, am I being charged twice?**

A: Yes, each API call is charged separately. To minimize cost:
- Draft prompts locally first
- Test with short inputs
- Commit working prompts to git to avoid re-testing

**Q: When should I extract the skill logic into prompts?**

A: Before your first handoff demo. Right now, fallback prompts are fine for development.

**Q: Should my notebooks be production-ready?**

A: Not yet. They should be *functional* and *clear*, but you can refine UX/polish later.

**Q: What if the lab owner wants to modify the prompts?**

A: They can! The prompts are text files. They can edit `prompts/*.txt` and the client will use their version.

---

## Next Actions

1. **Test the four notebooks** with your API key (cost: ~$0.35)
2. **Extract skill logic** from your 7 skills into `prompts/` files
3. **Build reference outputs** for 3–5 real drug targets
4. **Document decision trees** for each target in README
5. **Git commit** everything with clean commit messages

Then: **Demo to lab owner** with full GitHub repo + example outputs.

---

## Support

Questions during development? Ask in this Claude project.
