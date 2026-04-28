"""
ConversationHistory: loads, saves, and compresses the Anthropic message list
in SQLite so sessions survive browser closes and 30-min auth expiry.

Token efficiency design:
- After a sub-agent workflow step completes, the full tool-call exchange
  (~2000 tokens) is replaced with a ~150-token structured summary block.
- Full exchange is preserved in workflow_results for export/audit.
- The live messages list fed to the orchestrator stays small.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.engine import Connection

from src.database.conversation_db import (
    count_turns,
    delete_turns,
    load_turns,
    save_turn,
)
from src.database.session_db import update_research_session


class ConversationHistory:
    """In-memory conversation history backed by SQLite."""

    def __init__(
        self,
        research_session_id: str,
        conn: Connection,
    ) -> None:
        self.research_session_id = research_session_id
        self._conn = conn
        self._messages: list[dict] = []
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> list[dict]:
        """Load messages from SQLite. Call once at session start."""
        if not self._loaded:
            self._messages = load_turns(self._conn, self.research_session_id)
            self._loaded = True
        return self._messages

    @property
    def messages(self) -> list[dict]:
        if not self._loaded:
            self.load()
        return self._messages

    def add_user_turn(self, text: str) -> None:
        content = [{"type": "text", "text": text}]
        self._append_and_save("user", content)

    def add_assistant_turn(self, content_blocks: list[dict]) -> None:
        """content_blocks is the raw Anthropic content list (may include tool_use)."""
        self._append_and_save("assistant", content_blocks)

    def add_tool_result_turn(self, tool_results: list[dict]) -> None:
        """Add a user-role turn wrapping tool_result blocks (Anthropic format)."""
        self._append_and_save("user", tool_results)

    def compress_last_workflow(self, summary: dict) -> None:
        """
        Replace the last multi-turn tool exchange with a compact summary block.
        Keeps context window small while preserving legible history.

        summary keys: workflow_type, organism, protein, key_findings (str)
        """
        summary_block = {
            "type": "text",
            "text": (
                f"[WORKFLOW COMPLETE: {summary.get('workflow_type', 'unknown')}]\n"
                f"Target: {summary.get('organism', '')} / {summary.get('protein', '')}\n"
                f"{summary.get('key_findings', '')}"
            ),
        }
        # Find the last assistant turn with tool_use blocks and collapse it
        for i in range(len(self._messages) - 1, -1, -1):
            msg = self._messages[i]
            if msg["role"] == "assistant" and isinstance(msg["content"], list):
                has_tool_use = any(
                    b.get("type") == "tool_use" for b in msg["content"]
                    if isinstance(b, dict)
                )
                if has_tool_use:
                    self._messages[i] = {
                        "role": "assistant",
                        "content": [summary_block],
                    }
                    # Also remove the immediately following tool_result user turn
                    if i + 1 < len(self._messages) and self._messages[i + 1]["role"] == "user":
                        next_content = self._messages[i + 1].get("content", [])
                        if isinstance(next_content, list) and any(
                            b.get("type") == "tool_result" for b in next_content
                            if isinstance(b, dict)
                        ):
                            self._messages.pop(i + 1)
                    break

        # Persist compressed state: delete and re-save all turns
        delete_turns(self._conn, self.research_session_id)
        for idx, msg in enumerate(self._messages):
            save_turn(
                self._conn,
                self.research_session_id,
                idx,
                msg["role"],
                msg["content"],
            )

    def token_estimate(self) -> int:
        """Rough token estimate for the current message list (4 chars ≈ 1 token)."""
        raw = json.dumps(self._messages)
        return len(raw) // 4

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append_and_save(self, role: str, content: Any) -> None:
        idx = len(self._messages)
        self._messages.append({"role": role, "content": content})
        save_turn(self._conn, self.research_session_id, idx, role, content)
        update_research_session(self._conn, self.research_session_id)
