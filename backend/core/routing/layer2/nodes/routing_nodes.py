# core/routing/layer2/nodes/routing_nodes.py
from typing import Dict, Any, Optional

from core.routing.layer2.engine.base import BaseRoutingEngine
from core.routing.layer2.engine.laya_engine import LayaRoutingEngine
from schemas.request_models import AgentState

_DEFAULT_ENGINE: Optional[BaseRoutingEngine] = None


def get_routing_engine() -> BaseRoutingEngine:
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = LayaRoutingEngine()
    return _DEFAULT_ENGINE


def set_routing_engine(engine: BaseRoutingEngine):
    global _DEFAULT_ENGINE
    _DEFAULT_ENGINE = engine


def decide_after_tool_retrieval(state: AgentState) -> str:
    """
    Evaluates whether to bypass tool routing:
    - If explicit rag_only mode is active, or if no candidate tools matched AND the query
      is an explicit inquiry about uploaded documents, route to document_retrieval_node.
    - If no tools matched and the query is ordinary conversation, route directly to chat_node.
    - Otherwise, proceed to route_query for neural classification.
    """
    if state.get("rag_only"):
        return "document_retrieval_node"
    if not state.get("active_tools"):
        last_message = state["messages"][-1].content if state.get("messages") else ""
        from core.routing.layer2.heuristics import is_document_inquiry_query
        if is_document_inquiry_query(last_message):
            return "document_retrieval_node"
        return "chat_node"
    return "route_query"


def route_query(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates current user query against Top-K retrieved candidate tools
    using the active routing engine (default: LayaRoutingEngine).
    """
    last_message = state["messages"][-1].content
    active_tools = state.get("active_tools", [])
    rag_only = bool(state.get("rag_only"))

    engine = get_routing_engine()
    decision = engine.select_route(query=last_message, active_tools=active_tools, rag_only=rag_only)
    return {"next_route": decision.route}


def decide_next_step(state: AgentState) -> str:
    """Evaluates router output and targets a node execution branch."""
    route = state.get("next_route", "none")
    if route == "none":
        last_message = state["messages"][-1].content if state.get("messages") else ""
        from core.routing.layer2.heuristics import is_document_inquiry_query
        if state.get("rag_only") or is_document_inquiry_query(last_message):
            return "document_retrieval_node"
        return "chat_node"

    # Check if route is an uninstalled/dormant MCP pack stub
    active_tools = state.get("active_tools", [])
    tool_meta = next((t for t in active_tools if t.get("name") == route), None)
    if tool_meta and tool_meta.get("source_type") == "mcp_dormant":
        return "mcp_discovery_node"

    # Native tools or dynamically ingested mcp_active tools
    return "execute_tool_node"


def decide_discovery_step(state: AgentState) -> str:
    """Evaluates whether to loop back to tool_retrieval_node after MCP addition or finish."""
    route = state.get("next_route", "none")
    if route == "re_evaluate":
        return "tool_retrieval_node"
    return "summarize_conversation_node"

