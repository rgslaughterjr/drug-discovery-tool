"""SQLite-backed LangGraph checkpointer — singleton, created once per process.

Uses research_session_id as the thread_id so conversation state persists
across user reconnects without touching external services.
"""

from __future__ import annotations

import os
import pathlib

_async_saver = None
_sync_saver = None


def get_checkpointer_path() -> str:
    db_path = os.getenv("DB_PATH", "./data/research.db")
    pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_sync_checkpointer():
    """Return the singleton SqliteSaver (synchronous — for tests/CLI)."""
    global _sync_saver
    if _sync_saver is None:
        from langgraph.checkpoint.sqlite import SqliteSaver
        _sync_saver = SqliteSaver.from_conn_string(get_checkpointer_path())
    return _sync_saver


async def get_async_checkpointer():
    """Return the singleton AsyncSqliteSaver (for FastAPI request handlers)."""
    global _async_saver
    if _async_saver is None:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        _async_saver = AsyncSqliteSaver.from_conn_string(get_checkpointer_path())
    return _async_saver
