"""Base class for all Nemotron-powered sub-agents."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from src.agent.tools.tool_registry import SUB_AGENT_TOOLS, to_openai_format

# Dispatch map: tool name → async function
_TOOL_DISPATCH: dict | None = None


def _get_tool_dispatch() -> dict:
    global _TOOL_DISPATCH
    if _TOOL_DISPATCH is not None:
        return _TOOL_DISPATCH
    from src.agent.tools import (
        chembl,
        pdb,
        pubchem,
        rdkit_tools,
        uniprot,
    )
    _TOOL_DISPATCH = {
        "pubchem_compound_lookup": pubchem.pubchem_compound_lookup,
        "pubchem_bioactivity_search": pubchem.pubchem_bioactivity_search,
        "pubchem_similarity_search": pubchem.pubchem_similarity_search,
        "chembl_target_search": chembl.chembl_target_search,
        "chembl_bioactivity": chembl.chembl_bioactivity,
        "chembl_compound_detail": chembl.chembl_compound_detail,
        "uniprot_search": uniprot.uniprot_search,
        "uniprot_entry_detail": uniprot.uniprot_entry_detail,
        "pdb_structure_search": pdb.pdb_structure_search,
        "pdb_binding_site_info": pdb.pdb_binding_site_info,
        "validate_smiles": lambda smiles: rdkit_tools.validate_smiles(smiles),
        "calculate_molecular_properties": lambda smiles_list: rdkit_tools.calculate_molecular_properties(smiles_list),
        "screen_pains": lambda smiles_list: rdkit_tools.screen_pains(smiles_list),
        "compute_murcko_scaffolds": lambda smiles_list: rdkit_tools.compute_murcko_scaffolds(smiles_list),
        "generate_decoys": rdkit_tools.generate_decoys,
    }
    return _TOOL_DISPATCH


class BaseSubAgent:
    """
    Sub-agent powered by NVIDIA Nemotron (OpenAI-compatible) with a restricted tool subset.
    The orchestrator calls run(context) and receives a structured dict result.
    """

    agent_name: str = "base"
    max_iterations: int = 8

    def __init__(self, nvidia_api_key: str, model: str | None = None) -> None:
        from openai import OpenAI
        from src.config import NVIDIA_NIM_BASE_URL, SUB_AGENT_MODEL

        self._client = OpenAI(
            api_key=nvidia_api_key,
            base_url=NVIDIA_NIM_BASE_URL,
        )
        self._model = model or SUB_AGENT_MODEL
        self._tools_openai = to_openai_format(SUB_AGENT_TOOLS[self.agent_name])
        self._tool_calls_log: list[dict] = []

    def _load_system_prompt(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..",
            "prompts", f"sub_agent_{self.agent_name}.txt",
        )
        if os.path.exists(prompt_path):
            with open(prompt_path) as f:
                return f.read()
        return f"You are a specialized {self.agent_name} sub-agent for drug discovery."

    async def run(self, context: dict) -> dict:
        """
        Run the sub-agent tool-use loop.
        context: dict with keys like organism, protein, uniprot_id, pdb_id, chembl_target_id, etc.
        Returns structured result dict.
        """
        system_prompt = self._load_system_prompt()
        user_message = (
            f"Task context:\n{json.dumps(context, indent=2)}\n\n"
            "Complete the task described in your system prompt using the provided tools. "
            "Return your final answer as a JSON object."
        )

        messages: list[dict] = [{"role": "user", "content": user_message}]
        self._tool_calls_log = []

        for _ in range(self.max_iterations):
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=3000,
                tools=self._tools_openai,
                tool_choice="auto",
                messages=[{"role": "system", "content": system_prompt}] + messages,
            )

            choice = response.choices[0]
            messages.append({"role": "assistant", "content": choice.message.content,
                              "tool_calls": [tc.model_dump() for tc in (choice.message.tool_calls or [])]})

            if choice.finish_reason == "stop" or not choice.message.tool_calls:
                # Final answer
                text = choice.message.content or ""
                return self._parse_result(text)

            # Execute tool calls
            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                t0 = time.time()
                result = await self._dispatch_tool(fn_name, fn_args)
                elapsed_ms = int((time.time() - t0) * 1000)

                self._tool_calls_log.append({
                    "tool": fn_name,
                    "args": fn_args,
                    "result_summary": str(result)[:200],
                    "duration_ms": elapsed_ms,
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": fn_name,
                    "content": json.dumps(result),
                })

        return {"error": "Sub-agent exceeded max iterations", "agent": self.agent_name}

    async def _dispatch_tool(self, fn_name: str, fn_args: dict) -> Any:
        dispatch = _get_tool_dispatch()
        fn = dispatch.get(fn_name)
        if fn is None:
            return {"error": f"Unknown tool: {fn_name}"}
        try:
            import asyncio
            import inspect
            if inspect.iscoroutinefunction(fn):
                return await fn(**fn_args)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: fn(**fn_args))
        except Exception as e:
            return {"error": str(e), "tool": fn_name}

    def _parse_result(self, text: str) -> dict:
        """Try to extract JSON from the final assistant message."""
        text = text.strip()
        # Find JSON block
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        # Return as raw text if no valid JSON
        return {"raw_response": text, "agent": self.agent_name}

    @property
    def tool_calls_log(self) -> list[dict]:
        return self._tool_calls_log
