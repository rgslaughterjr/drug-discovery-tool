"""
Haiku synthesizer node — formats sub-agent structured output into user-facing prose.

Runs after every sub-agent node. Keeps the response concise and well-structured
so the user can act on it immediately.
"""

from __future__ import annotations

import json
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.state import ResearchState

_SYNTHESIZER_SYSTEM = """\
You are a concise scientific communicator for a drug discovery platform.
You receive structured JSON output from a specialized analysis agent and must present it \
clearly to a researcher.

Rules:
- Lead with the key finding in one sentence.
- Use bullet points or a markdown table for compound lists (name, SMILES, IC50/MW).
- Flag any PAINS alerts with ⚠️.
- End with a one-sentence recommendation for the next pipeline step.
- Do NOT repeat what the user already said.
- Maximum 400 words.
"""


def synthesizer_node(state: ResearchState) -> dict:
    """Format sub_agent_output into user-friendly prose using Claude Haiku."""
    api_key = state.get("_anthropic_api_key") or os.environ["ANTHROPIC_API_KEY"]
    model = os.getenv("HAIKU_MODEL", "claude-haiku-4-5-20251001")

    sub_agent_output = state.get("sub_agent_output") or {}

    llm = ChatAnthropic(
        model=model,
        api_key=api_key,
        max_tokens=1024,
        temperature=0,
    )

    prompt = (
        f"Sub-agent result:\n```json\n{json.dumps(sub_agent_output, indent=2)}\n```\n\n"
        "Present this to the researcher clearly and concisely."
    )

    response = llm.invoke([
        SystemMessage(content=_SYNTHESIZER_SYSTEM),
        HumanMessage(content=prompt),
    ])

    return {
        "messages": [response],
        "sub_agent_output": None,  # consumed — clear for next turn
    }
