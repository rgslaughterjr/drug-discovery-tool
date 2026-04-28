"""
Per-request context variables for API keys.

Keys are set once by the FastAPI request handler via contextvars.ContextVar
and read by any node that needs them. This keeps secrets out of LangGraph
state (which is checkpointed to SQLite and visible in LangSmith traces).
"""

from contextvars import ContextVar

# Set to the user's Anthropic API key at the start of each /api/agent/chat request.
anthropic_key: ContextVar[str] = ContextVar("anthropic_key", default="")

# Set to the NVIDIA NIM API key, or left as None if not configured.
nvidia_key: ContextVar[str | None] = ContextVar("nvidia_key", default=None)
