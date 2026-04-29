# Local Testing Guide

## Prerequisites

| Tool | Install |
|------|---------|
| Docker Desktop | https://docs.docker.com/get-docker/ |
| mkcert | `brew install mkcert` (macOS) / `sudo apt install mkcert` (Linux) |
| Anthropic API key | https://console.anthropic.com/ |
| NVIDIA API key (free) | https://build.nvidia.com/ — sign in, click "Get API Key" |

---

## First-Time Setup (one command)

```bash
cd drug-discovery-tool
bash dev/setup-local-env.sh
```

The script:
1. Checks Docker + mkcert are installed
2. Generates locally-trusted HTTPS certs (`dev/certs/local.pem`)
3. Creates `.env.local` from the template (you add keys here)
4. Starts Docker Compose (backend + frontend + nginx)

**Web UI:** https://localhost  
**API docs:** http://localhost:8000/docs  
**SQLite inspector:** `sqlite3 data/research.db`

---

## Subsequent Starts

```bash
docker compose -f dev/docker-compose.dev.yml --env-file .env.local up -d
```

## Stop

```bash
docker compose -f dev/docker-compose.dev.yml down
```

---

## Test Scenarios

### Scenario 1 — Agentic Mode: Evaluate Target
**Provider:** Anthropic  
**Input:** `"Evaluate Staphylococcus aureus GyrB as a drug target"`

Expected:
- AgentThinking panel shows: UniProt → PDB lookups
- WorkflowProgress bar advances to "Evaluate Target ✓"
- Text response includes GO/NO-GO, UniProt ID, best PDB ID
- structured_result event renders evaluation card (not compound table)

---

### Scenario 2 — Controls Generation (Fixes Hallucination)
**Input (continue from Scenario 1):** `"Generate validated controls"`

Expected:
- Agent calls chembl_target_search → chembl_bioactivity → chembl_compound_detail
- All SMILES validated with RDKit (validate_smiles calls visible in AgentThinking)
- CompoundTable renders with real PubChem/ChEMBL CIDs and measured IC50 values
- PAINS column shows "No" for clean compounds, "⚠ Yes" for flagged ones
- "PubChem" and "ChEMBL" links in each table row open real compound pages
- WorkflowProgress advances to "Generate Controls ✓"

**Verification:** Click the PubChem link for Novobiocin — it should open CID 54676895 on pubchem.ncbi.nlm.nih.gov.

---

### Scenario 3 — Prep Screening
**Input:** `"Design a screening campaign for this target"`

Expected:
- Agent calls pdb_binding_site_info for the PDB ID from the previous step (no re-entry needed)
- Pharmacophore features and ZINC20 query appear as a screening_brief structured result
- WorkflowProgress advances to "Prep Screening ✓"

---

### Scenario 4 — Follow-Up Question (Haiku routing)
**Input:** `"What does TPSA mean?"`

Expected:
- No tool calls in AgentThinking panel (routed to claude-haiku-4-5, not full tool loop)
- Quick concise response explaining topological polar surface area
- No new tool calls visible (token-efficient path)

---

### Scenario 5 — Classic Mode (Non-Anthropic provider)
**Setup:** Log in with OpenAI key instead of Anthropic

Expected:
- Classic Mode banner visible at bottom of chat
- No AgentThinking panel, no WorkflowProgress bar
- Responses come from legacy `/api/workflow/*` endpoints
- Warning message: "Switch to Anthropic for full agentic capabilities"

---

### Scenario 6 — Session Persistence
1. Run Scenarios 1-2 (evaluate + controls)
2. Note the research session in the chat
3. Close the browser tab
4. Re-open https://localhost
5. Log in again (new auth session, same Anthropic key)

Expected:
- The new agentic session starts fresh (new research session)
- Research sessions are stored in SQLite (check: `sqlite3 data/research.db "SELECT name, pipeline_stage FROM research_sessions;"`)

---

### Scenario 7 — Export
After generating controls (Scenario 2):
- Add an Export button test (once ExportButton component is wired — Phase E)
- Alternatively test directly: `curl -H "X-Session-ID: <id>" http://localhost:8000/api/export/<rs_id>/compounds.csv`

Expected: CSV file with all verified compounds, including CIDs, SMILES, MW, logP, IC50, PAINS flag.

---

### Scenario 8 — Session Cleanup
1. Click "✕" on SessionBadge
2. Confirm "End Session"
3. Try `GET /session/<old_id>/validate`

Expected:
- Auth session deleted from memory
- `{"valid": false}` response
- Research session data remains in SQLite (persistent across auth sessions)

---

## Security Checklist

| Check | How to verify |
|-------|--------------|
| API key not in localStorage | DevTools → Application → Local Storage → empty |
| API key not in sessionStorage | DevTools → Application → Session Storage → only sessionId |
| API key not in SSE stream | DevTools → Network → EventStream tab → no `api_key` field |
| NVIDIA key not exposed to frontend | DevTools → Network → no `nvapi-` in any response |
| X-Session-ID in all /api/ requests | DevTools → Network → Headers → confirm header present |
| SQLite has no API keys | `sqlite3 data/research.db "SELECT * FROM research_sessions;"` — no api_key column |
| HTTPS on localhost:443 | Browser shows padlock, no certificate warning |
| No LangSmith telemetry | Wireshark / `tcpdump` — no requests to `smith.langchain.com` |

---

## Inspecting SQLite

```bash
sqlite3 data/research.db

# List all research sessions
SELECT id, name, organism, pipeline_stage, last_active_at FROM research_sessions;

# View conversation turns for a session
SELECT turn_index, role, substr(content_json, 1, 100) FROM conversation_turns WHERE research_session_id = '<id>';

# View verified compounds
SELECT name, compound_type, pubchem_cid, activity_value_nm, is_pains FROM verified_compounds;
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `https://localhost` certificate warning | Run `mkcert -install` then restart browser |
| Backend 401 on /api/agent/chat | Confirm ANTHROPIC_API_KEY is set in .env.local |
| Sub-agent returns error | Confirm NVIDIA_API_KEY is set and has free NIM access |
| RDKit tools return `rdkit-pypi not installed` | `docker compose build --no-cache` (triggers pip install rdkit-pypi) |
| SQLite "unable to open" | Check DB_PATH in .env.local; ensure `data/` directory exists |
| Frontend not hot-reloading | Restart frontend container: `docker compose -f dev/docker-compose.dev.yml restart frontend` |
