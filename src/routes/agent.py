"""
Agentic endpoints:
  POST /api/agent/chat                   — SSE streaming via LangGraph
  POST /api/agent/research-sessions      — create research session
  GET  /api/agent/research-sessions      — list sessions for current auth session
  GET  /api/agent/research-sessions/{id} — get session detail + conversation
  DELETE /api/agent/research-sessions/{id}
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
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
# Request models
# ---------------------------------------------------------------------------

class AgentChatRequest(BaseModel):
    message: str
    research_session_id: Optional[str] = None


class CreateResearchSessionRequest(BaseModel):
    name: Optional[str] = None


# ---------------------------------------------------------------------------
# POST /api/agent/chat  — LangGraph SSE streaming
# ---------------------------------------------------------------------------

@router.post("/chat")
async def agent_chat_sse(
    request: Request,
    request_body: AgentChatRequest,
    x_session_id: Optional[str] = Header(None),
):
    auth = _require_session(x_session_id)
    provider: str = session_store.get_provider(x_session_id)

    if provider != "anthropic":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Agentic mode requires an Anthropic API key. "
                f"Provider '{provider}' should use the classic /api/workflow/* endpoints."
            ),
        )

    anthropic_api_key: str = session_store.get_api_key(x_session_id)
    nvidia_api_key: str | None = os.getenv("NVIDIA_API_KEY")
    engine: Engine = request.app.state.db_engine

    # Resolve or create the research session
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
        from langchain_core.messages import HumanMessage
        from src.agent.graph import build_graph
        from src.agent.streaming import error_event, langgraph_events_to_sse

        try:
            checkpointer = await _get_checkpointer()
            graph = build_graph(checkpointer=checkpointer)

            # Initial state for this turn
            initial_state = {
                "messages": [HumanMessage(content=request_body.message)],
                "research_session_id": research_session_id,
                "auth_session_id": x_session_id,
                "provider": provider,
                "model": session_store.get_model(x_session_id),
                "pipeline_stage": "idle",
                "delegate_to": None,
                "sub_agent_output": None,
                # Pass API keys via state so nodes don't need global env vars
                "_anthropic_api_key": anthropic_api_key,
                "_nvidia_api_key": nvidia_api_key,
            }

            config = {"configurable": {"thread_id": research_session_id}}

            event_stream = graph.astream_events(
                initial_state,
                config=config,
                version="v2",
            )

            async for sse_line in langgraph_events_to_sse(event_stream, research_session_id):
                yield sse_line

        except Exception as e:
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


async def _get_checkpointer():
    """Lazily create the async SQLite checkpointer."""
    from src.agent.checkpointer import make_async_checkpointer
    return await make_async_checkpointer()


# ---------------------------------------------------------------------------
# Research session CRUD
# ---------------------------------------------------------------------------

@router.post("/research-sessions")
async def create_session(
    request: Request,
    body: CreateResearchSessionRequest,
    x_session_id: Optional[str] = Header(None),
):
    _require_session(x_session_id)
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
