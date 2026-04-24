"""
FastAPI application for Drug Discovery Web UI.

Endpoints:
- POST /session/create — Create new session with credentials
- GET /session/{id}/validate — Check session status
- DELETE /session/{id} — Logout and cleanup
- GET /api/models/available — List available models
- POST /api/workflow/evaluate-target — Run target evaluation
- POST /api/workflow/get-controls — Generate controls
- POST /api/workflow/prep-screening — Prepare screening
- POST /api/workflow/analyze-hits — Analyze hits
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import session, models, workflows

# Create FastAPI app
app = FastAPI(
    title="Drug Discovery Agent API",
    description="AI-assisted drug discovery pipeline with multi-provider LLM support",
    version="1.0.0",
)

# CORS configuration (allow localhost:3000 for React dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(session.router)
app.include_router(models.router)
app.include_router(workflows.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "drug-discovery-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
