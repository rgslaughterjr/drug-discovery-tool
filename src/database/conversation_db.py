"""ConversationTurn CRUD operations."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select, update, delete
from sqlalchemy.engine import Connection

from .models import conversation_turns


def save_turn(
    conn: Connection,
    research_session_id: str,
    turn_index: int,
    role: str,
    content: list[dict] | str,
) -> int:
    """Insert a conversation turn. content can be a list of Anthropic content blocks."""
    content_json = json.dumps(content) if not isinstance(content, str) else content
    result = conn.execute(
        conversation_turns.insert().values(
            research_session_id=research_session_id,
            turn_index=turn_index,
            role=role,
            content_json=content_json,
            is_compressed=False,
            created_at=datetime.utcnow(),
        )
    )
    conn.commit()
    return result.lastrowid


def load_turns(conn: Connection, research_session_id: str) -> list[dict]:
    """Load all turns for a session, ordered by turn_index."""
    rows = conn.execute(
        select(conversation_turns)
        .where(conversation_turns.c.research_session_id == research_session_id)
        .order_by(conversation_turns.c.turn_index)
    ).mappings().all()

    messages = []
    for row in rows:
        content = json.loads(row["content_json"])
        messages.append({"role": row["role"], "content": content})
    return messages


def compress_turn(conn: Connection, turn_id: int, summary_content: list[dict]) -> None:
    """Replace a turn's content with a compressed summary and mark it compressed."""
    conn.execute(
        update(conversation_turns)
        .where(conversation_turns.c.id == turn_id)
        .values(
            content_json=json.dumps(summary_content),
            is_compressed=True,
        )
    )
    conn.commit()


def count_turns(conn: Connection, research_session_id: str) -> int:
    rows = conn.execute(
        select(conversation_turns.c.id)
        .where(conversation_turns.c.research_session_id == research_session_id)
    ).all()
    return len(rows)


def delete_turns(conn: Connection, research_session_id: str) -> None:
    conn.execute(
        delete(conversation_turns)
        .where(conversation_turns.c.research_session_id == research_session_id)
    )
    conn.commit()
