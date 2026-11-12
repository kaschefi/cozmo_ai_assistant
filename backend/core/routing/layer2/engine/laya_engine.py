# core/routing/layer2/engine/laya_engine.py
import re
import threading
import sys
import os
from typing import List, Dict, Any, Optional

os.environ["USE_TF"] = "0"
import laya

from core.routing.layer2.config import Layer2Config, DEFAULT_CONFIG
from core.routing.layer2.heuristics import (
    is_file_operation_query,
    is_workstation_setup_query,
    filter_setup_tools,
)
from core.routing.layer2.engine.base import BaseRoutingEngine, RouteDecisionResult

_LAYA_AGENT = None
_LAYA_LOCK = threading.Lock()


def get_laya_agent(model_id: str = DEFAULT_CONFIG.laya_model_id):
    """Singleton getter for the LAYA Typed Decision Model."""
    global _LAYA_AGENT
    if _LAYA_AGENT is None:
        with _LAYA_LOCK:
            if _LAYA_AGENT is None:
                print(f"[LayaRouter] Pre-loading LAYA Typed Decision Model '{model_id}'...")
                _LAYA_AGENT = laya.load(model_id)
                print("[LayaRouter] LAYA Decision Model initialized successfully.")
    return _LAYA_AGENT


def _get_active_laya_getter():
    gn = sys.modules.get("core.routing.layer2.graph_nodes")
    if gn and hasattr(gn, "get_laya_agent"):
        return gn.get_laya_agent
    return get_laya_agent


class LayaRoutingEngine(BaseRoutingEngine):
    """Production 2-Layer Cognitive Router using LAYA Typed Decision Models."""

    def __init__(self, config: Layer2Config = DEFAULT_CONFIG):
        self.config = config

    @staticmethod
    def _slugify(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

    def _prepare_tool_criteria(
        self, active_tools: List[Dict[str, Any]], catalog: Dict[str, Any]
    ) -> tuple[Dict[str, str], Dict[str, str]]:
        laya_to_tool_name = {}
        tools_dict = {}
        for tool in active_tools:
            t_name = tool["name"]
            laya_key = t_name
            source_type = tool.get("source_type")
            pack_id = tool.get("server_pack_id") or (t_name if source_type == "mcp_dormant" else None)
            display_name = catalog.get(pack_id, {}).get("display_name") if pack_id else None
            if display_name:
                dn_slug = self._slugify(display_name)
                if dn_slug:
                    if source_type == "mcp_dormant":
                        laya_key = dn_slug
                    elif source_type == "mcp_active":
                        laya_key = f"{dn_slug}_{t_name}"
            while laya_key in tools_dict:
                laya_key = f"{laya_key}_"
            tools_dict[laya_key] = tool.get("description", "")
            laya_to_tool_name[laya_key] = t_name

        tools_dict["none"] = (
            "Core conversational channel. Use for casual chat, greetings, social pleasantries, asking about "
            "identity/personality, sharing personal facts or hobbies, philosophical discussion, small talk, "
            "or uploaded document discussion."
        )
        return tools_dict, laya_to_tool_name

    def select_route(
        self,
        query: str,
        active_tools: List[Dict[str, Any]],
        rag_only: bool = False,
    ) -> RouteDecisionResult:
        if rag_only or not active_tools:
            return RouteDecisionResult(route="none")

        # Strict rule: Filter out workstation setups if query is not an explicit setup command
        active_tools = filter_setup_tools(active_tools, query, self.config.setup_exclusion_names)

        # Strict rule: If user query is a file operation request, remove setup_coding from options
        if is_file_operation_query(query):
            active_tools = [t for t in active_tools if t.get("name") != "setup_coding"]
            if not active_tools:
                return RouteDecisionResult(route="mcp_pack_filesystem", confidence=1.0)

        if not active_tools:
            return RouteDecisionResult(route="none")

        # Bound candidates to at most max_candidate_tools to prevent logit collapse
        active_tools = active_tools[: self.config.max_candidate_tools]

        catalog = {}
        try:
            from core.routing.layer2.mcp_manager import mcp_manager
            catalog = mcp_manager.get_catalog()
        except Exception:
            catalog = {}

        tools_dict, laya_to_tool_name = self._prepare_tool_criteria(active_tools, catalog)

        instructions = (
            "Select the appropriate tool or service to handle the user's request, question, or command. "
            "Use 'web_search_node' whenever the user wants to look up information, search the web, check company market data, sports results, or news. "
            "Select 'none' only if the user is simply chatting, greeting, sharing personal facts, asking about identity, or making casual small talk."
        )

        questions = {
            "tool_selection": {
                "type": "choice",
                "instructions": instructions,
                "criteria": tools_dict,
            }
        }

        try:
            agent_getter = _get_active_laya_getter()
            agent = agent_getter(self.config.laya_model_id)
            result = agent.predict(query, questions)
            answers = result.get("answers", result)
            decision = answers.get("tool_selection", {})
            raw_choice = decision.get("choice", "none")
            confidence = decision.get("confidence", 0.0)
            selected_route = laya_to_tool_name.get(raw_choice, raw_choice)
        except Exception as e:
            print(f"[route_query Error] Laya prediction failed: {e}. Falling back to 'none'.")
            selected_route = "none"
            confidence = 0.0
            decision = {}

        # Guard 1: If setup_coding was selected despite a file operation intent, redirect to filesystem
        if (selected_route == "setup_coding" or raw_choice == "setup_coding") and is_file_operation_query(query):
            print(f"[route_query Guard] Blocked setup_coding for file operation query: '{query}'. Redirecting to filesystem.")
            fs_tool = next(
                (
                    t["name"]
                    for t in active_tools
                    if t.get("name") != "setup_coding"
                    and ("file" in t["name"] or t.get("server_pack_id") == "mcp_pack_filesystem")
                ),
                "mcp_pack_filesystem",
            )
            selected_route = fs_tool
            confidence = 1.0
        # Guard 2: Workstation launchers should NEVER trigger on non-setup queries
        elif selected_route in self.config.setup_exclusion_names and not is_workstation_setup_query(query):
            print(f"[route_query Guard] Blocked {selected_route} for non-setup query: '{query}'. Routing to conversational chat_node.")
            selected_route = "none"

        # Confidence Gating for "none":
        # If "none" is chosen with low confidence (< 0.12) but FAISS retrieved an extremely strong
        # domain match (top_score <= 0.65), override "none" with the highest-probability tool candidate.
        top_score = active_tools[0].get("score", 1.0) if active_tools else 1.0
        if (
            selected_route == "none"
            and confidence < self.config.none_override_max_conf
            and top_score <= self.config.none_override_strong_match
        ):
            probs = decision.get("probabilities", {})
            tool_probs = {laya_to_tool_name.get(k, k): v for k, v in probs.items() if k != "none"}
            if tool_probs:
                best_tool = max(tool_probs, key=tool_probs.get)
                if tool_probs.get(best_tool, 0.0) >= self.config.none_override_min_prob:
                    selected_route = best_tool

        # Anti-hallucination gating from Two-Layer Top-K:
        # If LAYA picked a tool with flat noise confidence (< 0.05) and FAISS had only a weak match (> 0.82),
        # treat the query as conversational and route to 'none'.
        if (
            selected_route != "none"
            and confidence < self.config.anti_hallucination_min_conf
            and top_score > self.config.anti_hallucination_weak_score
        ):
            # Guardrail: do not clobber filesystem tools when file operation was explicitly requested
            if not (is_file_operation_query(query) and ("file" in selected_route or "filesystem" in selected_route)):
                selected_route = "none"

        return RouteDecisionResult(
            route=selected_route,
            confidence=confidence,
            raw_choice=raw_choice,
            details=decision,
        )
