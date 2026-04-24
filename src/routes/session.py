"""Session management endpoints."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from src.session_manager import get_session_store

router = APIRouter(prefix="/session", tags=["session"])


class CreateSessionRequest(BaseModel):
    provider: str
    api_key: str
    model: str


class CreateSessionResponse(BaseModel):
    session_id: str
    session_expires_in: int


class ValidateSessionResponse(BaseModel):
    valid: bool
    provider: Optional[str]
    model: Optional[str]
    session_expires_in: Optional[int]


@router.post("/create", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new session with user credentials.
    API key stored in-memory only (RAM), never persisted.
    """
    store = get_session_store()
    session_id = store.create(
        provider=request.provider,
        api_key=request.api_key,
        model=request.model,
    )
    expires_in = store.get_expires_in(session_id)
    return {
        "session_id": session_id,
        "session_expires_in": expires_in or 1800,
    }


@router.get("/{session_id}/validate", response_model=ValidateSessionResponse)
async def validate_session(session_id: str):
    """Validate if a session is still active."""
    store = get_session_store()
    valid = store.validate(session_id)

    if valid:
        provider = store.get_provider(session_id)
        model = store.get_model(session_id)
        expires_in = store.get_expires_in(session_id)
        return {
            "valid": True,
            "provider": provider,
            "model": model,
            "session_expires_in": expires_in,
        }
    else:
        return {
            "valid": False,
            "provider": None,
            "model": None,
            "session_expires_in": None,
        }


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Logout and delete session.
    API key is securely overwritten in memory before deletion.
    """
    store = get_session_store()
    deleted = store.delete(session_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "status": "success",
        "message": "Session deleted. All credentials securely wiped.",
    }
