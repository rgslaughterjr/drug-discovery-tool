# Drug Discovery Web UI Agent - Progress Ledger

**Project Goal:** Build a web UI for university students/professors to interact with the drug discovery agent in natural language, using their own LLM API keys with complete privacy guarantees.

---

## Phase 0: Codebase Refactoring ✅ COMPLETE

**Status:** Jupyter notebooks refactored to pure Python modules.

**Deliverables:**
- `src/workflows/evaluate_target.py` — Workflow 1: Target evaluation
- `src/workflows/get_controls.py` — Workflow 2: Control compound generation
- `src/workflows/prep_screening.py` — Workflow 3: Screening campaign design
- `src/workflows/analyze_hits.py` — Workflow 4: Hit prioritization
- `src/workflows/__init__.py` — Package initialization
- `test_workflows.py` — Standalone test script (all 4 workflows verified)

**Architecture:**
- Each workflow = one clean Python function
- Takes typed parameters, returns structured dict output
- No notebook cells, no interactive prompts, no display logic
- Stateless (suitable for stateless API endpoints)
- Auto-creates DrugDiscoveryClient if not provided
- Backward compatible with existing DrugDiscoveryClient

**Key Changes:**
- Removed: Jupyter-specific imports, interactive user prompts, file I/O
- Added: Type hints, docstrings, structured returns, error handling
- Maintained: All original logic, system prompts, LLM integration

**Next:** Phase 1 - Backend session manager + FastAPI foundation

---

## Phase 1: Backend Foundation & Integration
**Status:** ⏳ PENDING APPROVAL

---

## Phase 2: Frontend Setup
**Status:** 📋 PENDING PHASE 1 ✅

---

## Phase 3: Chat Integration
**Status:** 📋 PENDING PHASE 2 ✅

---

## Phase 4: Testing & Security
**Status:** 📋 PENDING PHASE 3 ✅

---

## Phase 5: Deployment & Docs
**Status:** 📋 PENDING PHASE 4 ✅

---

## Architecture Notes

### Workflow Module Design
- **Initialization:** Client auto-creates if not provided (useful for testing)
- **Return Format:** All return `{"status": "success", "task": "...", ...response data...}`
- **No Side Effects:** No file I/O, no console output, pure function semantics
- **Error Handling:** DrugDiscoveryClient errors propagate naturally (will be caught by FastAPI)

### Integration Path
- FastAPI `/api/workflow/{type}` routes receive session_id + parameters
- Routes instantiate workflows with session-scoped DrugDiscoveryClient
- Session manager injects provider + api_key into APIConfig
- Workflow returns structured result → FastAPI wraps with `session_expires_in`

### Token Budget Status
- **Phase 0 used:** ~1,800 tokens (under 3,500 budget) ✅
- **Remaining for remaining phases:** ~16,700 tokens
