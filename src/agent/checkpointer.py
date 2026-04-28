"""SQLite-backed LangGraph checkpointer.

Uses research_session_id as the thread_id so conversation state persists
across user reconnects without touching external services.
"""

from __future__ import annotations

import os
import pathlib


def get_checkpointer_path() -> str:
    db_path = os.getenv("DB_PATH", "./data/research.db")
    pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return db_path


def make_sync_checkpointer():
    """Return a SqliteSaver for use in synchronous contexts (tests, CLI)."""
    from langgraph.checkpoint.sqlite import SqliteSaver
    return SqliteSaver.from_conn_string(get_checkpointer_path())


async def make_async_checkpointer():
    """Return an AsyncSqliteSaver for use in async FastAPI request handlers."""
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    return AsyncSqliteSaver.from_conn_string(get_checkpointer_path())
