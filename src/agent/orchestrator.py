"""
OrchestratorAgent — the main streaming agent powering /api/agent/chat.

Model: claude-sonnet-4-6 (Anthropic) for tool use + routing
Sub-agents: Nemotron (NVIDIA NIM) for scientific heavy lifting
Summary synthesis: claude-haiku-4-5 for concise user-facing responses

Token efficiency measures:
- Conversation history compressed after each workflow step (~150 tokens vs ~2000)
- Tool results trimmed to essential fields before injection into context
- Follow-up questions routed to Haiku; tool-use loop only for new workflow steps
- Per-session tool result cache prevents duplicate API calls
"""

from __future__ import annotations

import json
import os
import time
from typing import AsyncGenerator

from sqlalchemy.engine import Connection

from src.agent.conversation import ConversationHistory
from src.agent.streaming import (
    SSEEvent,
    done_event,
    error_event,
    structured_result_event,
    sub_agent_done_event,
    sub_agent_start_event,
    text_delta_event,
    thinking_event,
    tool_result_event,
)
from src.agent.tools.tool_registry import ORCHESTRATOR_TOOLS
from src.config import HAIKU_MODEL, ORCHESTRATOR_MODEL
from src.database.session_db import get_research_session, update_research_session


_FOLLOWUP_KEYWORDS = frozenset([
    "what", "why", "how", "explain", "meaning", "define", "what is", "can you",
    "tell me", "describe", "summarize", "show me again", "what does", "clarify",
])

_SUB_AGENT_MAP = {
    "target_evaluator": "src.agent.sub_agents.target_evaluator.TargetEvaluatorAgent",
    "controls_generator": "src.agent.sub_agents.controls_generator.ControlsGeneratorAgent",
    "screening_designer": "src.agent.sub_agents.screening_designer.ScreeningDesignerAgent",
    "hits_analyzer": "src.agent.sub_agents.hits_analyzer.HitsAnalyzerAgent",
}

_PIPELINE_STAGE_ORDER = ["evaluate", "controls", "screening", "hits"]


class OrchestratorAgent:
    def __init__(
        self,
        anthropic_api_key: str,
        nvidia_api_key: str | None,
        research_session_id: str,
        conn: Connection,
        orchestrator_model: str = ORCHESTRATOR_MODEL,
        haiku_model: str = HAIKU_MODEL,
    ) -> None:
        from anthropic import AsyncAnthropic

        self._anthropic = AsyncAnthropic(api_key=anthropic_api_key)
        self._nvidia_api_key = nvidia_api_key
        self._research_session_id = research_session_id
        self._conn = conn
        self._orchestrator_model = orchestrator_model
        self._haiku_model = haiku_model
        self._history = ConversationHistory(research_session_id, conn)
        self._tool_cache: dict[str, dict] = {}  # key: "tool_name:arg_hash" → result

    async def run_streaming(
        self, user_message: str
    ) -> AsyncGenerator[SSEEvent, None]:
        """Main entry point. Yields SSEEvent objects for the SSE endpoint to forward."""
        self._history.load()
        self._history.add_user_turn(user_message)

        session_data = get_research_session(self._conn, self._research_session_id) or {}
        system_prompt = self._build_system_prompt(session_data)

        # Route simple follow-ups to Haiku to save tokens
        if self._is_followup(user_message) and len(self._history.messages) > 2:
            async for event in self._haiku_response(system_prompt, user_message):
                yield event
            return

        try:
            async for event in self._orchestrator_loop(system_prompt):
                yield event
        except Exception as e:
            yield error_event(f"Orchestrator error: {e}")

        yield done_event(self._research_session_id)

    # ------------------------------------------------------------------
    # Orchestrator tool-use loop
    # ------------------------------------------------------------------

    async def _orchestrator_loop(
        self, system_prompt: str
    ) -> AsyncGenerator[SSEEvent, None]:
        messages = self._history.messages

        async with self._anthropic.messages.stream(
            model=self._orchestrator_model,
            max_tokens=4096,
            system=system_prompt,
            tools=ORCHESTRATOR_TOOLS,
            messages=messages,
        ) as stream:
            content_blocks: list[dict] = []
            current_tool_use: dict | None = None
            text_so_far = ""

            async for event in stream:
                etype = event.type

                if etype == "content_block_start":
                    block = event.content_block
                    if block.type == "text":
                        current_tool_use = None
                    elif block.type == "tool_use":
                        current_tool_use = {
                            "id": block.id,
                            "name": block.name,
                            "input_str": "",
                        }
                        yield thinking_event(block.name)

                elif etype == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        yield text_delta_event(delta.text)
                        text_so_far += delta.text
                    elif delta.type == "input_json_delta" and current_tool_use:
                        current_tool_use["input_str"] += delta.partial_json

                elif etype == "content_block_stop":
                    if current_tool_use:
                        try:
                            tool_input = json.loads(current_tool_use["input_str"] or "{}")
                        except json.JSONDecodeError:
                            tool_input = {}
                        current_tool_use["input"] = tool_input
                        content_blocks.append({
                            "type": "tool_use",
                            "id": current_tool_use["id"],
                            "name": current_tool_use["name"],
                            "input": tool_input,
                        })
                        current_tool_use = None
                    elif text_so_far:
                        content_blocks.append({"type": "text", "text": text_so_far})
                        text_so_far = ""

                elif etype == "message_stop":
                    break

        # Save assistant turn
        self._history.add_assistant_turn(content_blocks)

        # Process tool calls if any
        tool_result_blocks = []
        for block in content_blocks:
            if block.get("type") != "tool_use":
                continue
            tool_name = block["name"]
            tool_input = block.get("input", {})

            t0 = time.time()
            if tool_name == "delegate_to_sub_agent":
                async for event in self._handle_sub_agent(tool_input):
                    yield event
                result = {"delegated": True, "agent": tool_input.get("agent_name")}
            else:
                result = await self._dispatch_tool(tool_name, tool_input)
                elapsed_ms = int((time.time() - t0) * 1000)
                yield tool_result_event(tool_name, result, elapsed_ms)
                # Update session metadata from tool results
                self._extract_session_metadata(tool_name, result)

            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": [{"type": "text", "text": json.dumps(result)}],
            })

        if tool_result_blocks:
            self._history.add_tool_result_turn(tool_result_blocks)
            # Recurse: send tool results back to orchestrator for next turn
            async for event in self._orchestrator_loop(
                self._build_system_prompt(
                    get_research_session(self._conn, self._research_session_id) or {}
                )
            ):
                yield event

    # ------------------------------------------------------------------
    # Sub-agent delegation
    # ------------------------------------------------------------------

    async def _handle_sub_agent(
        self, delegation_input: dict
    ) -> AsyncGenerator[SSEEvent, None]:
        agent_name = delegation_input.get("agent_name", "")
        context = delegation_input.get("context", {})

        if not self._nvidia_api_key:
            yield error_event(
                "Sub-agent delegation requires NVIDIA_API_KEY. "
                "Add your free NVIDIA NIM key in settings."
            )
            return

        yield sub_agent_start_event(agent_name)

        class_path = _SUB_AGENT_MAP.get(agent_name)
        if not class_path:
            yield error_event(f"Unknown sub-agent: {agent_name}")
            return

        module_path, class_name = class_path.rsplit(".", 1)
        import importlib
        module = importlib.import_module(module_path)
        AgentClass = getattr(module, class_name)

        agent_instance = AgentClass(nvidia_api_key=self._nvidia_api_key)
        result = await agent_instance.run(context)

        # Determine result type for frontend display
        result_type = _RESULT_TYPE_MAP.get(agent_name, "analysis_result")
        yield sub_agent_done_event(agent_name, result_type, result)

        # Emit compound table if controls were generated
        if agent_name == "controls_generator":
            positives = result.get("positive_controls", [])
            negatives = result.get("negative_controls", [])
            if positives or negatives:
                yield structured_result_event("compound_table", positives + [
                    {**n, "compound_type": "negative_control"} for n in negatives
                ])
            # Compress history after controls workflow
            self._history.compress_last_workflow({
                "workflow_type": "get_controls",
                "organism": context.get("organism", ""),
                "protein": context.get("protein", ""),
                "key_findings": (
                    f"Generated {len(positives)} positive controls and "
                    f"{len(negatives)} negative controls. "
                    f"Best IC50: {min((c.get('activity_nm', 9999) for c in positives), default='N/A')} nM."
                ),
            })
            self._advance_pipeline_stage("controls")

        elif agent_name == "target_evaluator":
            yield structured_result_event("evaluation_result", result)
            self._history.compress_last_workflow({
                "workflow_type": "evaluate_target",
                "organism": context.get("organism", ""),
                "protein": context.get("protein", ""),
                "key_findings": (
                    f"Recommendation: {result.get('recommendation', 'N/A')}. "
                    f"Best PDB: {result.get('best_pdb_id', 'None')} "
                    f"({result.get('best_resolution_angstrom', '?')} Å). "
                    f"{result.get('rationale', '')}"
                ),
            })
            self._advance_pipeline_stage("evaluate")
            # Store verified IDs in session
            if result.get("uniprot_id"):
                update_research_session(
                    self._conn, self._research_session_id,
                    uniprot_id=result["uniprot_id"],
                    pdb_id=result.get("best_pdb_id"),
                )

        elif agent_name == "screening_designer":
            yield structured_result_event("screening_brief", result)
            self._history.compress_last_workflow({
                "workflow_type": "prep_screening",
                "organism": context.get("organism", ""),
                "protein": context.get("protein", ""),
                "key_findings": (
                    f"Pharmacophore designed from PDB {result.get('pdb_id', '?')}. "
                    f"{len(result.get('pharmacophore_features', []))} features ranked. "
                    f"Est. library: {result.get('estimated_library_size', '?')}."
                ),
            })
            self._advance_pipeline_stage("screening")

        elif agent_name == "hits_analyzer":
            purchase_list = result.get("purchase_list", [])
            if purchase_list:
                yield structured_result_event("compound_table", purchase_list)
            self._history.compress_last_workflow({
                "workflow_type": "analyze_hits",
                "organism": context.get("organism", ""),
                "protein": context.get("protein", ""),
                "key_findings": (
                    f"Score cutoff: {result.get('score_cutoff', '?')}. "
                    f"{result.get('total_hits_above_cutoff', 0)} hits above cutoff. "
                    f"{len(purchase_list)} compounds in purchase list."
                ),
            })
            self._advance_pipeline_stage("hits")

    # ------------------------------------------------------------------
    # Tool dispatch (orchestrator level)
    # ------------------------------------------------------------------

    async def _dispatch_tool(self, tool_name: str, tool_input: dict) -> dict:
        cache_key = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
        if cache_key in self._tool_cache:
            return self._tool_cache[cache_key]

        from src.agent.tools import chembl, pdb, pubchem, rdkit_tools, uniprot

        dispatch = {
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

        fn = dispatch.get(tool_name)
        if not fn:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            import asyncio
            import inspect
            if inspect.iscoroutinefunction(fn):
                result = await fn(**tool_input)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: fn(**tool_input))
            self._tool_cache[cache_key] = result
            return result
        except Exception as e:
            return {"error": str(e), "tool": tool_name}

    # ------------------------------------------------------------------
    # Haiku shortcut for follow-up questions
    # ------------------------------------------------------------------

    async def _haiku_response(
        self, system_prompt: str, user_message: str
    ) -> AsyncGenerator[SSEEvent, None]:
        async with self._anthropic.messages.stream(
            model=self._haiku_model,
            max_tokens=512,
            system=system_prompt,
            messages=self._history.messages,
        ) as stream:
            full_text = ""
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield text_delta_event(event.delta.text)
                    full_text += event.delta.text

        self._history.add_assistant_turn([{"type": "text", "text": full_text}])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_system_prompt(self, session_data: dict) -> str:
        prompt_path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            "prompts", "orchestrator_system.txt",
        )
        if os.path.exists(prompt_path):
            with open(prompt_path) as f:
                template = f.read()
        else:
            template = "You are an expert drug discovery orchestrator. {RESEARCH_SESSION_CONTEXT}"

        context_lines = []
        if session_data.get("organism"):
            context_lines.append(f"- Organism: {session_data['organism']}")
        if session_data.get("target_protein"):
            context_lines.append(f"- Target protein: {session_data['target_protein']}")
        if session_data.get("uniprot_id"):
            context_lines.append(f"- UniProt ID: {session_data['uniprot_id']}")
        if session_data.get("pdb_id"):
            context_lines.append(f"- Best PDB ID: {session_data['pdb_id']}")
        if session_data.get("chembl_target_id"):
            context_lines.append(f"- ChEMBL target ID: {session_data['chembl_target_id']}")
        if session_data.get("pipeline_stage"):
            context_lines.append(f"- Pipeline stage completed: {session_data['pipeline_stage']}")

        ctx = "\n".join(context_lines) if context_lines else "(No prior context — new research session)"
        return template.replace("{RESEARCH_SESSION_CONTEXT}", ctx)

    def _is_followup(self, message: str) -> bool:
        lower = message.lower().strip()
        return any(lower.startswith(kw) for kw in _FOLLOWUP_KEYWORDS) and len(lower) < 120

    def _extract_session_metadata(self, tool_name: str, result: dict) -> None:
        if not isinstance(result, dict):
            return
        updates: dict = {}
        if tool_name == "uniprot_search":
            entries = result.get("entries", [])
            if entries:
                updates["uniprot_id"] = entries[0].get("uniprot_id")
                updates["target_protein"] = entries[0].get("gene_name") or entries[0].get("protein_name")
                org = entries[0].get("organism")
                if org:
                    updates["organism"] = org
        elif tool_name == "chembl_target_search":
            targets = result.get("targets", [])
            if targets:
                updates["chembl_target_id"] = targets[0].get("chembl_id")
        elif tool_name == "pdb_structure_search":
            structs = result.get("structures", [])
            if structs:
                updates["pdb_id"] = structs[0].get("pdb_id")
        if updates:
            update_research_session(self._conn, self._research_session_id, **updates)

    def _advance_pipeline_stage(self, stage: str) -> None:
        current = (get_research_session(self._conn, self._research_session_id) or {}).get("pipeline_stage")
        try:
            current_idx = _PIPELINE_STAGE_ORDER.index(current) if current else -1
            new_idx = _PIPELINE_STAGE_ORDER.index(stage)
            if new_idx > current_idx:
                update_research_session(
                    self._conn, self._research_session_id, pipeline_stage=stage
                )
        except ValueError:
            pass


_RESULT_TYPE_MAP = {
    "target_evaluator": "evaluation_result",
    "controls_generator": "compound_table",
    "screening_designer": "screening_brief",
    "hits_analyzer": "compound_table",
}
