# Drug Discovery Agent — Internal Reference

> **Status: Active development. Not production-ready.**
> This document is an internal reference for development and debugging.

---

## System Overview

A four-stage AI-augmented virtual screening pipeline implemented as a LangGraph `StateGraph`. The orchestrator (Claude Sonnet) routes user requests to domain tools or Nemotron sub-agents, which query real public databases (PubChem, ChEMBL, UniProt, RCSB PDB) and run local cheminformatics (RDKit). Claude Haiku synthesizes sub-agent results into concise researcher-facing prose.

The web UI is a React/TypeScript chat interface backed by a FastAPI SSE stream. Conversation state persists across sessions via SQLite (LangGraph `AsyncSqliteSaver`). LangSmith traces are emitted automatically when `LANGCHAIN_TRACING_V2=true`.

---

## Architecture

```
User (React — SSE)
  └── OrchestratorNode  [claude-sonnet-4-6]
        ├── ToolNode  (regular DB + RDKit calls)
        │     ├── PubChem REST    — compound lookup, similarity, bioactivity
        │     ├── ChEMBL REST     — target search, IC50/Ki data
        │     ├── UniProt REST    — protein function, GO terms, essentiality
        │     ├── RCSB PDB REST   — structure search, binding site residues
        │     └── RDKit (local)   — SMILES validation, PAINS, Murcko scaffolds
        │
        └── Sub-Agent Nodes  [nvidia/llama-3.1-nemotron-70b-instruct via NIM]
              ├── target_evaluator   — UniProt + PDB druggability
              ├── controls_generator — ChEMBL + PubChem IC50-verified controls
              ├── screening_designer — PDB binding site pharmacophore design
              └── hits_analyzer      — hit prioritization + PAINS + scaffold
                    └── SynthesizerNode  [claude-haiku-4-5-20251001]
```

### Graph nodes

| Node | Model | Max tokens | Purpose |
|------|-------|-----------|---------|
| `orchestrator` | `claude-sonnet-4-6` | 4096 | Routes, calls tools, delegates |
| `tools` | — | — | `ToolNode` executing DB/RDKit calls |
| `target_evaluator` | Nemotron-70b | 4096 | UniProt + PDB druggability loop |
| `controls_generator` | Nemotron-70b | 4096 | ChEMBL/PubChem control generation |
| `screening_designer` | Nemotron-70b | 4096 | Pharmacophore + binding site |
| `hits_analyzer` | Nemotron-70b | 4096 | Hit ranking + PAINS filter |
| `synthesizer` | `claude-haiku-4-5-20251001` | 512 | Formats sub-agent JSON → prose |

**Prompt caching:** The orchestrator's system message (~300 tok) + 16 tool schemas (~1,700 tok) = ~2,000 cached tokens per call at ~10% cost (Anthropic ephemeral cache, 5-min TTL).

**Runaway protection:** Orchestrator hard-caps at 6 turns per request (`orchestrator_turns` in `ResearchState`). Sub-agents cap at 5 tool-call iterations.

---

## Four Pipeline Stages

| Stage | Trigger phrase | Sub-agent | Key tools |
|-------|---------------|-----------|-----------|
| Evaluate Target | "evaluate [protein]" | `target_evaluator` | `uniprot_search`, `pdb_structure_search` |
| Generate Controls | "generate controls" / "find inhibitors" | `controls_generator` | `chembl_bioactivity`, `pubchem_compound_lookup`, `screen_pains`, `generate_decoys` |
| Prepare Screening | "design screening" / "pharmacophore" | `screening_designer` | `pdb_binding_site_info`, `calculate_molecular_properties` |
| Analyze Hits | "analyze hits" / "rank compounds" | `hits_analyzer` | `pubchem_compound_lookup`, `compute_murcko_scaffolds`, `screen_pains` |

---

## File Structure

```
drug-discovery-tool/
├── src/
│   ├── agent/
│   │   ├── context.py          # Per-request ContextVar for API keys (never in state)
│   │   ├── graph.py            # StateGraph topology + build_graph()
│   │   ├── state.py            # ResearchState TypedDict
│   │   ├── checkpointer.py     # Singleton AsyncSqliteSaver
│   │   ├── streaming.py        # SSEEvent + langgraph_events_to_sse()
│   │   ├── nodes/
│   │   │   ├── orchestrator.py # Claude Sonnet node + route_after_orchestrator()
│   │   │   ├── sub_agents.py   # Four Nemotron nodes + parallel tool execution
│   │   │   ├── synthesizer.py  # Claude Haiku node
│   │   │   └── tools.py        # @tool wrappers + per-sub-agent subsets
│   │   └── tools/
│   │       ├── pubchem.py      # PubChem REST calls (trimmed responses)
│   │       ├── chembl.py       # ChEMBL REST calls
│   │       ├── uniprot.py      # UniProt REST calls
│   │       ├── pdb.py          # RCSB PDB REST calls
│   │       └── rdkit_tools.py  # SMILES validation, PAINS, Murcko, decoys
│   ├── database/
│   │   ├── models.py           # SQLAlchemy table definitions
│   │   ├── session_db.py       # ResearchSession CRUD
│   │   ├── conversation_db.py  # ConversationTurn CRUD
│   │   └── results_db.py       # WorkflowResult + VerifiedCompound CRUD
│   ├── routes/
│   │   ├── agent.py            # POST /api/agent/chat (SSE) + research session CRUD
│   │   ├── export.py           # GET /api/export/{id}/compounds.csv + /results.json
│   │   ├── session.py          # Auth session create/validate/delete
│   │   ├── models.py           # GET /api/models/available
│   │   └── workflows.py        # Legacy /api/workflow/* endpoints
│   ├── workflows/              # Legacy Python workflow functions (non-agentic)
│   │   ├── evaluate_target.py
│   │   ├── get_controls.py
│   │   ├── prep_screening.py
│   │   └── analyze_hits.py
│   ├── main.py                 # FastAPI app, CORS, startup SQLite init
│   ├── session_manager.py      # In-memory auth session store (30-min TTL)
│   ├── api_client.py           # Legacy multi-provider LLM client
│   └── config.py               # Environment variable loader
├── prompts/
│   ├── orchestrator_system.txt
│   ├── sub_agent_target.txt
│   ├── sub_agent_controls.txt
│   ├── sub_agent_screening.txt
│   └── sub_agent_hits.txt
├── web/                        # React/TypeScript frontend
│   └── src/
│       ├── components/         # ChatInterface, LoginModal, SessionBadge, etc.
│       ├── context/            # SessionContext
│       ├── hooks/              # useAgentStream, useSessionCleanup
│       └── utils/              # apiClient, sseParser
├── tests/
│   ├── agent/                  # Graph routing + state tests
│   ├── database/               # CRUD unit tests
│   ├── routes/                 # FastAPI route tests (TestClient)
│   └── tools/                  # RDKit + streaming tests
├── dev/                        # Local dev environment
│   ├── docker-compose.dev.yml
│   ├── nginx.conf
│   └── setup-local-env.sh
├── .env.example                # All environment variable templates
├── requirements.txt
└── pytest.ini
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in values.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes | — | Orchestrator + Haiku synthesizer |
| `NVIDIA_API_KEY` | Yes | — | Nemotron sub-agents via NIM free tier |
| `LANGCHAIN_TRACING_V2` | No | `false` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | If tracing | — | LangSmith key (`ls__...`) |
| `LANGCHAIN_PROJECT` | No | `drug-discovery-tool` | LangSmith project name |
| `ORCHESTRATOR_MODEL` | No | `claude-sonnet-4-6` | Override orchestrator model |
| `SUB_AGENT_MODEL` | No | `nvidia/llama-3.1-nemotron-70b-instruct` | Override Nemotron model |
| `HAIKU_MODEL` | No | `claude-haiku-4-5-20251001` | Override synthesizer model |
| `DB_PATH` | No | `./data/research.db` | SQLite file path |
| `REACT_APP_API_URL` | No | `http://localhost:8000` | Frontend → backend URL |

---

## Running Locally

**Prerequisites:** Python 3.11+, Node 18+

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY and NVIDIA_API_KEY

# 3. Start FastAPI backend (port 8000, hot-reload)
uvicorn src.main:app --reload --port 8000

# 4. In a second terminal — start React dev server (port 3000)
cd web && npm install && BROWSER=none npm start
```

Both servers are also started automatically on Claude Code Desktop session start via `.claude/settings.json` hooks, with the Preview pane pointing at `http://localhost:3000`.

Health check: `curl http://localhost:8000/health` → `{"status":"ok","version":"2.0.0"}`

---

## API Endpoints

### Agentic (Anthropic only)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/agent/chat` | SSE stream — LangGraph orchestrator turn |
| `POST` | `/api/agent/research-sessions` | Create research session |
| `GET` | `/api/agent/research-sessions` | List sessions for auth session |
| `GET` | `/api/agent/research-sessions/{id}` | Session detail + conversation length |
| `DELETE` | `/api/agent/research-sessions/{id}` | Delete session |
| `GET` | `/api/export/{id}/compounds.csv` | Download verified compounds as CSV |
| `GET` | `/api/export/{id}/results.json` | Download full workflow results as JSON |

### Legacy (all providers)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/session/create` | Create auth session (returns session ID) |
| `GET` | `/session/{id}/validate` | Check session validity + TTL |
| `DELETE` | `/session/{id}` | Delete auth session |
| `GET` | `/api/models/available` | List supported providers + models |
| `POST` | `/api/workflow/evaluate-target` | Legacy single-call evaluate |
| `POST` | `/api/workflow/get-controls` | Legacy single-call controls |
| `POST` | `/api/workflow/prep-screening` | Legacy single-call screening |
| `POST` | `/api/workflow/analyze-hits` | Legacy single-call hits |

All protected endpoints require `X-Session-ID` header.

### SSE event format (`/api/agent/chat`)

```json
{"type": "thinking",          "tool": "chembl_bioactivity", "status": "calling"}
{"type": "tool_result",       "tool": "chembl_bioactivity", "data": {}, "duration_ms": 420}
{"type": "text_delta",        "content": "Found 14 inhibitors..."}
{"type": "sub_agent_delegated","agent": "controls_generator", "status": "running"}
{"type": "structured_result", "result_type": "compound_table", "data": [...]}
{"type": "error",             "message": "ChEMBL API timeout"}
{"type": "done",              "research_session_id": "abc-123"}
```

---

## Database Schema

Four SQLite tables defined in `src/database/models.py`:

```
research_sessions
  id (UUID PK), auth_session_id (idx), name, organism, target_protein,
  uniprot_id, pdb_id, chembl_target_id, pipeline_stage,
  created_at, last_active_at, provider, model

conversation_turns
  id (INT PK), research_session_id (FK→cascade), turn_index,
  role ("user"|"assistant"), content_json (TEXT), is_compressed (BOOL),
  created_at

workflow_results
  id (UUID PK), research_session_id (FK→cascade), workflow_type,
  result_json (TEXT), tool_calls_json (TEXT audit log),
  model_used, created_at, is_verified (BOOL)

verified_compounds
  id (INT PK), workflow_result_id (FK), research_session_id (FK→cascade),
  compound_type ("positive_control"|"negative_control"|"hit"),
  name, pubchem_cid, chembl_id, smiles, canonical_smiles,
  mw, logp, tpsa, hbd, hba, activity_value_nm, activity_type,
  is_pains, pains_alerts, docking_score, rank, notes
```

---

## Cost Profile

Estimated token usage per full 4-stage agentic pipeline run:

| Stage | Orchestrator | Sub-agent (Nemotron) | Synthesizer (Haiku) |
|-------|-------------|---------------------|---------------------|
| Evaluate Target | ~800 tok | ~3,000 tok (free NIM) | ~300 tok |
| Generate Controls | ~800 tok | ~6,000 tok (free NIM) | ~400 tok |
| Prepare Screening | ~800 tok | ~4,000 tok (free NIM) | ~350 tok |
| Analyze Hits | ~800 tok | ~4,000 tok (free NIM) | ~350 tok |

Orchestrator prompt caching (~2,000 tokens cached per turn at ~10% cost) reduces effective Sonnet input cost by ~70% on multi-turn conversations. Nemotron sub-agent calls are free under NVIDIA NIM's free tier. Haiku synthesis is the cheapest Anthropic model.

Rough full-pipeline cost (Anthropic tokens only): **$0.05–$0.15** depending on target complexity and number of follow-up questions.

---

## Running Tests

```bash
# All unit tests (excludes integration tests that hit live APIs)
pytest -m "not integration" -v

# Specific test modules
pytest tests/agent/ -v
pytest tests/database/ -v
pytest tests/routes/ -v

# RDKit tests (requires rdkit installed)
pytest tests/tools/test_rdkit_tools.py -v
```

CI is currently paused (`workflow_dispatch` only). Re-enable by restoring `push`/`pull_request` triggers in `.github/workflows/ci.yml`.
