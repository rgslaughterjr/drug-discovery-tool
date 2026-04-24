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

## Phase 1: Backend Foundation & Integration ✅ COMPLETE

**Status:** Session manager, FastAPI app, routes, and NLP router implemented.

**Deliverables:**
- `src/session_manager.py` — In-memory session store with 30-min TTL and secure key handling
- `src/main.py` — FastAPI app with CORS (localhost:3000) and route registration
- `src/routes/session.py` — Session endpoints (create, validate, delete)
- `src/routes/models.py` — Model discovery endpoint (Anthropic, OpenAI, Gemini, Cohere, Mistral)
- `src/routes/workflows.py` — Workflow integration (evaluate, controls, screening, analyze)
- `src/nlp_router.py` — Keyword-based NLP router (maps user input → workflow)
- `test_backend.py` — Standalone API tests

**Architecture:**
- Session storage: In-memory dict (no persistence to disk/database)
- Security: API key overwritten before deletion, auto-expire after 30 min
- API routes: X-Session-ID header validates all requests
- Workflow integration: Routes extract session credentials, pass to DrugDiscoveryClient
- Model data: Hardcoded list (Anthropic, OpenAI, Google, Cohere, Mistral) with costs/capabilities

**Key Features:**
- ✅ Create session with provider + api_key + model
- ✅ Validate session (returns expires_in)
- ✅ Delete session (secure key overwrite + removal)
- ✅ Model discovery (6 providers, 20+ models)
- ✅ All 4 workflow routes (evaluate, controls, screening, analyze)
- ✅ Error handling (401 on invalid/expired session, 500 on workflow error)
- ✅ CORS enabled for React frontend (localhost:3000)

**Next:** Phase 2 - Frontend setup (React LoginModal + SessionContext)

---

## Phase 2: Frontend Setup ✅ COMPLETE

**Status:** React project scaffolding + LoginModal + SessionContext implemented.

**Deliverables:**
- `web/package.json` — Dependencies (React 18, TypeScript, Axios)
- `web/tsconfig.json` — TypeScript configuration
- `web/public/index.html` — HTML entry point with base styles
- `web/src/context/SessionContext.tsx` — Session state management (React Context)
- `web/src/hooks/useSessionCleanup.ts` — Cleanup hook (beforeunload + inactivity timeout)
- `web/src/components/LoginModal.tsx` — Login form + API integration
- `web/src/components/LoginModal.css` — Styled login modal
- `web/src/App.tsx` — Main app (conditional render based on session)
- `web/src/App.css` — App styling
- `web/src/index.tsx` — React entry point
- `web/.env.example` — Environment variables template
- `web/.gitignore` — Exclude node_modules, .env, etc.

**Key Features:**
- ✅ SessionContext: Holds session_id, provider, model, expiresIn (no API key stored)
- ✅ LoginModal: 7 provider options, API key input (masked), model field (editable)
- ✅ Confirmation checkbox: "I understand my API key will be deleted when I close this window"
- ✅ Form validation: Requires agreed checkbox + apiKey before submit
- ✅ Error handling: Displays message if session creation fails
- ✅ useSessionCleanup: Handles beforeunload + 30-min inactivity timeout
- ✅ TypeScript: Full type safety across components
- ✅ Styling: Basic CSS (expandable for Tailwind/Material-UI)

**Architecture:**
- React Context for session state (no Redux needed)
- sessionStorage for sessionId only (NOT apiKey)
- axios for API calls to http://localhost:8000
- REACT_APP_API_URL env var (defaults to localhost:8000)

**Next:** Phase 3 - ChatInterface + ModelSelector + Integration

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
