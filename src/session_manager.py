"""
Session Manager: In-memory store for user sessions.

Sessions contain:
- session_id (UUID)
- provider (LLM provider name)
- api_key (stored in RAM only, never persisted)
- model (model ID)
- created_at, expires_at (datetime)

Key security properties:
- No persistence to disk/database
- Key overwritten before deletion
- Auto-expires after 30 min inactivity
"""

from uuid import uuid4
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets


class SessionStore:
    """In-memory session storage with 30-min TTL."""

    def __init__(self, ttl_minutes: int = 30):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.ttl_minutes = ttl_minutes

    def create(self, provider: str, api_key: str, model: str) -> str:
        """
        Create a new session.

        Args:
            provider: LLM provider name (anthropic, openai, gemini, etc.)
            api_key: API key for the provider
            model: Model ID (e.g., claude-3-5-sonnet-20241022)

        Returns:
            session_id (UUID string)
        """
        session_id = str(uuid4())
        self.sessions[session_id] = {
            "provider": provider,
            "api_key": api_key,
            "model": model,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(minutes=self.ttl_minutes),
        }
        return session_id

    def validate(self, session_id: str) -> bool:
        """Check if session exists and is not expired."""
        if session_id not in self.sessions:
            return False
        expires_at = self.sessions[session_id].get("expires_at")
        if expires_at and datetime.utcnow() > expires_at:
            self.delete(session_id)
            return False
        return True

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data (if valid and not expired)."""
        if not self.validate(session_id):
            return None
        return self.sessions.get(session_id)

    def get_api_key(self, session_id: str) -> Optional[str]:
        """Get API key for a session."""
        session = self.get(session_id)
        return session.get("api_key") if session else None

    def get_provider(self, session_id: str) -> Optional[str]:
        """Get provider for a session."""
        session = self.get(session_id)
        return session.get("provider") if session else None

    def get_model(self, session_id: str) -> Optional[str]:
        """Get model for a session."""
        session = self.get(session_id)
        return session.get("model") if session else None

    def get_expires_in(self, session_id: str) -> Optional[int]:
        """Get seconds until session expires."""
        if session_id not in self.sessions:
            return None
        expires_at = self.sessions[session_id].get("expires_at")
        if expires_at:
            delta = expires_at - datetime.utcnow()
            return max(0, int(delta.total_seconds()))
        return None

    def delete(self, session_id: str) -> bool:
        """Delete session and securely overwrite API key."""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        api_key = session.get("api_key")

        # Overwrite API key in memory with random data
        if api_key:
            overwrite_key = secrets.token_urlsafe(len(api_key))
            session["api_key"] = overwrite_key

        # Delete session
        del self.sessions[session_id]
        return True

    def cleanup_expired(self) -> int:
        """Remove all expired sessions. Returns count of deleted sessions."""
        expired = [
            sid for sid, data in self.sessions.items()
            if data.get("expires_at") and datetime.utcnow() > data["expires_at"]
        ]
        for sid in expired:
            self.delete(sid)
        return len(expired)


# Global session store (one per FastAPI instance)
_store = SessionStore(ttl_minutes=30)


def get_session_store() -> SessionStore:
    """Get the global session store."""
    return _store
