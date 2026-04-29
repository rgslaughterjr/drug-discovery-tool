"""ResearchSession CRUD operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update, delete
from sqlalchemy.engine import Connection

from .models import research_sessions


def create_research_session(
    conn: Connection,
    auth_session_id: str,
    provider: str,
    model: str,
    name: str | None = None,
) -> str:
    """Insert a new research session row. Returns the new UUID."""
    rs_id = str(uuid.uuid4())
    conn.execute(
        research_sessions.insert().values(
            id=rs_id,
            auth_session_id=auth_session_id,
            provider=provider,
            model=model,
            name=name or "Untitled Research",
            created_at=datetime.utcnow(),
            last_active_at=datetime.utcnow(),
        )
    )
    conn.commit()
    return rs_id


def get_research_session(conn: Connection, rs_id: str) -> dict | None:
    row = conn.execute(
        select(research_sessions).where(research_sessions.c.id == rs_id)
    ).mappings().first()
    return dict(row) if row else None


def list_research_sessions(conn: Connection, auth_session_id: str) -> list[dict]:
    rows = conn.execute(
        select(research_sessions)
        .where(research_sessions.c.auth_session_id == auth_session_id)
        .order_by(research_sessions.c.last_active_at.desc())
    ).mappings().all()
    return [dict(r) for r in rows]


def update_research_session(conn: Connection, rs_id: str, **fields) -> None:
    fields["last_active_at"] = datetime.utcnow()
    conn.execute(
        update(research_sessions)
        .where(research_sessions.c.id == rs_id)
        .values(**fields)
    )
    conn.commit()


def delete_research_session(conn: Connection, rs_id: str) -> None:
    conn.execute(
        delete(research_sessions).where(research_sessions.c.id == rs_id)
    )
    conn.commit()
