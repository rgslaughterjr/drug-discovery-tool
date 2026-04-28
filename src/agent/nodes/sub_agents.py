"""
Nemotron sub-agent nodes — one per pipeline stage.

Each node:
  1. Extracts the task from the delegate_to_sub_agent tool call in the last message.
  2. Runs a focused tool-calling loop using NVIDIA Nemotron via NIM (OpenAI-compatible).
  3. Returns the structured result as a ToolMessage so the orchestrator sees it,
     plus sets sub_agent_output for the Haiku synthesizer.

LangSmith traces each sub-agent run as a named node within the parent graph run.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from src.agent import context as _ctx
from src.agent.nodes.tools import (
    CONTROLS_GENERATOR_TOOLS,
    HITS_ANALYZER_TOOLS,
    SCREENING_DESIGNER_TOOLS,
    TARGET_EVALUATOR_TOOLS,
)
from src.agent.state import ResearchState

_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
_MAX_ITER = 5


def _load_prompt(name: str) -> str:
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "prompts", f"sub_agent_{name}.txt"
    )
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return f"You are a specialized {name} sub-agent for drug discovery. Use your tools to complete the task and return a JSON result."


def _extract_task(state: ResearchState) -> tuple[str, dict, str | None]:
    """Extract task_description, context, and tool_call_id from the last delegation call."""
    for msg in reversed(list(state["messages"])):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] == "delegate_to_sub_agent":
                    args = tc.get("args", {})
                    return (
                        args.get("task_description", "Complete the assigned drug discovery task."),
                        args.get("context") or {},
                        tc.get("id"),
                    )
    return ("Complete the assigned drug discovery task.", {}, None)


async def _invoke_tool(tool_fn, args: dict) -> dict:
    """Invoke a single tool asynchronously, returning a JSON-serialisable result."""
    try:
        raw = await tool_fn.ainvoke(args)
        return raw if isinstance(raw, dict) else {"result": raw}
    except Exception as e:
        return {"error": str(e), "tool": tool_fn.name}


async def _run_sub_agent(
    agent_name: str,
    tools: list,
    state: ResearchState,
) -> tuple[dict, str | None]:
    """Core Nemotron tool-calling loop — shared by all four sub-agent nodes."""
    nvidia_api_key = _ctx.nvidia_key.get() or os.getenv("NVIDIA_API_KEY")
    if not nvidia_api_key:
        raise ValueError(
            "NVIDIA_API_KEY is required for Nemotron sub-agents. "
            "Set it in your environment or pass it at login."
        )
    model_name = os.getenv("SUB_AGENT_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")

    task_description, context, tool_call_id = _extract_task(state)
    system_prompt = _load_prompt(agent_name)

    llm = ChatOpenAI(
        model=model_name,
        base_url=_NIM_BASE_URL,
        api_key=nvidia_api_key,
        temperature=0,
        max_tokens=4096,
    ).bind_tools(tools)

    user_content = (
        f"Task: {task_description}\n\n"
        f"Context:\n{json.dumps(context, indent=2)}\n\n"
        "Complete the task using your tools. Return your final answer as a JSON object."
    )

    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage as LCToolMessage
    messages: list = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    result: dict = {"agent": agent_name, "error": "Max iterations reached"}

    for _ in range(_MAX_ITER):
        response = await llm.ainvoke(messages)
        messages.append(response)

        if not (hasattr(response, "tool_calls") and response.tool_calls):
            # Final answer — extract JSON from response text
            text = response.content or ""
            start, end = text.find("{"), text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    result = json.loads(text[start:end])
                    result.setdefault("agent", agent_name)
                    break
                except json.JSONDecodeError:
                    pass
            result = {"agent": agent_name, "raw_response": text}
            break

        # Execute all tool calls in parallel
        tool_map = {t.name: t for t in tools}
        calls = response.tool_calls

        tool_results = await asyncio.gather(
            *[
                _invoke_tool(tool_map[tc["name"]], tc["args"])
                if tc["name"] in tool_map
                else asyncio.coroutine(lambda: {"error": f"Unknown tool: {tc['name']}"})()
                for tc in calls
            ]
        )

        for tc, tool_result in zip(calls, tool_results):
            messages.append(
                LCToolMessage(
                    content=json.dumps(tool_result),
                    tool_call_id=tc["id"],
                )
            )

    return result, tool_call_id


async def _make_sub_agent_node(agent_name: str, tools: list, state: ResearchState) -> dict:
    result, tool_call_id = await _run_sub_agent(agent_name, tools, state)

    # Return as ToolMessage so the orchestrator's tool_call is resolved,
    # plus store structured output for the Haiku synthesizer.
    messages = []
    if tool_call_id:
        messages.append(
            ToolMessage(
                content=json.dumps(result),
                tool_call_id=tool_call_id,
                name="delegate_to_sub_agent",
            )
        )

    return {
        "messages": messages,
        "sub_agent_output": result,
        "delegate_to": None,  # clear delegation flag
    }


async def target_evaluator_node(state: ResearchState) -> dict:
    return await _make_sub_agent_node("target_evaluator", TARGET_EVALUATOR_TOOLS, state)


async def controls_generator_node(state: ResearchState) -> dict:
    return await _make_sub_agent_node("controls_generator", CONTROLS_GENERATOR_TOOLS, state)


async def screening_designer_node(state: ResearchState) -> dict:
    return await _make_sub_agent_node("screening_designer", SCREENING_DESIGNER_TOOLS, state)


async def hits_analyzer_node(state: ResearchState) -> dict:
    return await _make_sub_agent_node("hits_analyzer", HITS_ANALYZER_TOOLS, state)
