"""
Agentic endpoints:
  POST /api/agent/chat                   — SSE streaming orchestrator
  POST /api/agent/research-sessions      — create research session
  GET  /api/agent/research-sessions      — list sessions for current auth session
  GET  /api/agent/research-sessions/{id} — get session detail + conversation
  DELETE /api/agent/research-sessions/{id}
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.engine import Connection, Engine

from src.database.conversation_db import load_turns
from src.database.results_db import get_verified_compounds, get_workflow_results
from src.database.session_db import (
    create_research_session,
    delete_research_session,
    get_research_session,
    list_research_sessions,
)
from src.session_manager import _store as session_store

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# DB dependency
# ---------------------------------------------------------------------------

def get_db(request) -> Connection:  # type: ignore[override]
    engine: Engine = request.app.state.db_engine
    with engine.connect() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _require_session(x_session_id: str | None) -> dict:
    if not x_session_id:
        raise HTTPException(status_code=401, detail="X-Session-ID header required")
    session = session_store.get(x_session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return session


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AgentChatRequest(BaseModel):
    message: str
    research_session_id: Optional[str] = None


class CreateResearchSessionRequest(BaseModel):
    name: Optional[str] = None


# ---------------------------------------------------------------------------
# POST /api/agent/chat  — SSE streaming
# ---------------------------------------------------------------------------

from fastapi import Request


@router.post("/chat")
async def agent_chat_sse(
    request: Request,
    request_body: AgentChatRequest,
    x_session_id: Optional[str] = Header(None),
):
    auth = _require_session(x_session_id)
    anthropic_api_key: str = session_store.get_api_key(x_session_id)
    provider: str = session_store.get_provider(x_session_id)

    if provider != "anthropic":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Agentic mode requires an Anthropic API key. "
                f"Your current provider '{provider}' uses the classic /api/workflow/* endpoints."
            ),
        )

    engine: Engine = request.app.state.db_engine
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")

    # Create a new research session if none provided
    research_session_id = request_body.research_session_id
    with engine.connect() as conn:
        if not research_session_id:
            research_session_id = create_research_session(
                conn,
                auth_session_id=x_session_id,
                provider=provider,
                model=session_store.get_model(x_session_id),
            )
        else:
            if not get_research_session(conn, research_session_id):
                raise HTTPException(status_code=404, detail="Research session not found")

    async def event_generator():
        from src.agent.orchestrator import OrchestratorAgent

        with engine.connect() as conn:
            agent = OrchestratorAgent(
                anthropic_api_key=anthropic_api_key,
                nvidia_api_key=nvidia_api_key,
                research_session_id=research_session_id,
                conn=conn,
            )
            try:
                async for event in agent.run_streaming(request_body.message):
                    yield event.to_sse_line()
            except Exception as e:
                from src.agent.streaming import error_event
                yield error_event(str(e)).to_sse_line()
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Research session CRUD
# ---------------------------------------------------------------------------

@router.post("/research-sessions")
async def create_session(
    request: Request,
    body: CreateResearchSessionRequest,
    x_session_id: Optional[str] = Header(None),
):
    auth = _require_session(x_session_id)
    engine: Engine = request.app.state.db_engine
    with engine.connect() as conn:
        rs_id = create_research_session(
            conn,
            auth_session_id=x_session_id,
            provider=session_store.get_provider(x_session_id),
            model=session_store.get_model(x_session_id),
            name=body.name,
        )
    return {"research_session_id": rs_id, "status": "created"}


@router.get("/research-sessions")
async def list_sessions(
    request: Request,
    x_session_id: Optional[str] = Header(None),
):
    _require_session(x_session_id)
    engine: Engine = request.app.state.db_engine
    with engine.connect() as conn:
        sessions = list_research_sessions(conn, x_session_id)
    return {"sessions": sessions}


@router.get("/research-sessions/{rs_id}")
async def get_session(
    rs_id: str,
    request: Request,
    x_session_id: Optional[str] = Header(None),
):
    _require_session(x_session_id)
    engine: Engine = request.app.state.db_engine
    with engine.connect() as conn:
        session = get_research_session(conn, rs_id)
        if not session or session["auth_session_id"] != x_session_id:
            raise HTTPException(status_code=404, detail="Research session not found")
        turns = load_turns(conn, rs_id)
        results = get_workflow_results(conn, rs_id)
    return {"session": session, "conversation_length": len(turns), "workflow_results": results}


@router.delete("/research-sessions/{rs_id}")
async def delete_session(
    rs_id: str,
    request: Request,
    x_session_id: Optional[str] = Header(None),
):
    _require_session(x_session_id)
    engine: Engine = request.app.state.db_engine
    with engine.connect() as conn:
        session = get_research_session(conn, rs_id)
        if not session or session["auth_session_id"] != x_session_id:
            raise HTTPException(status_code=404, detail="Research session not found")
        delete_research_session(conn, rs_id)
    return {"status": "deleted", "research_session_id": rs_id}
