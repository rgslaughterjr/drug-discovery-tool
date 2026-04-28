"""
FastAPI application for Drug Discovery Web UI.

Legacy endpoints (all providers):
- POST /session/create
- GET /session/{id}/validate
- DELETE /session/{id}
- GET /api/models/available
- POST /api/workflow/evaluate-target
- POST /api/workflow/get-controls
- POST /api/workflow/prep-screening
- POST /api/workflow/analyze-hits

New agentic endpoints (Anthropic + NVIDIA NIM):
- POST /api/agent/chat              — SSE streaming orchestrator
- GET/POST/DELETE /api/agent/research-sessions/*
- GET /api/export/{id}/compounds.csv
- GET /api/export/{id}/results.json
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routes import session, models, workflows

app = FastAPI(
    title="Drug Discovery Agent API",
    description="AI-assisted drug discovery pipeline with multi-provider LLM support",
    version="2.0.0",
)

# CORS: allow React dev server and local HTTPS (mkcert)
_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost",
    "https://127.0.0.1",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Legacy routes (untouched)
app.include_router(session.router)
app.include_router(models.router)
app.include_router(workflows.router)


@app.on_event("startup")
def _startup() -> None:
    """Initialize SQLite database on first run."""
    import pathlib
    from src.config import DB_PATH
    from src.database.models import create_engine_from_path, init_db

    db_file = pathlib.Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine_from_path(str(db_file))
    init_db(engine)
    # Store engine on app state so routes can access it
    app.state.db_engine = engine


def _register_agent_routes() -> None:
    """Register new agentic routes if dependencies are available."""
    try:
        from src.routes import agent as agent_router
        from src.routes import export as export_router
        app.include_router(agent_router.router)
        app.include_router(export_router.router)
    except ImportError:
        pass  # Agent routes created in Phase B; silently skip until then


_register_agent_routes()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "drug-discovery-api", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
