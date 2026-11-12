# core/routing/layer2/graph_nodes.py
"""
Facade for Layer 2 Graph Nodes.
Abstracted into modular subcomponents:
- config: Centralized Layer 2 hyperparameters and thresholds.
- heuristics: Intent classifiers and query preprocessors.
- engine: Abstract BaseRoutingEngine & LayaRoutingEngine.
- nodes: Isolated LangGraph node handlers (memory, retrieval, routing, summary, mcp).
"""
import os
import sys
import threading
from typing import List, Optional

os.environ["USE_TF"] = "0"
import laya

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, RemoveMessage
from langsmith import traceable

from core.routing.llm_factory import get_llm
from core.routing.layer2.tool_vector_db import tool_rag_registry
from schemas.memory_db import long_term_memory
from schemas.request_models import AgentState, RouteDecision

try:
    from test.routers.tools import TOOL_TO_DOMAIN
except Exception:
    TOOL_TO_DOMAIN = {}

GRAY = "\033[90m"
RESET = "\033[0m"

from core.routing.layer2.config import DEFAULT_CONFIG
_SETUP_EXCLUSION_NAMES = DEFAULT_CONFIG.setup_exclusion_names

from core.routing.layer2.engine.laya_engine import (
    _LAYA_AGENT,
    _LAYA_LOCK,
    get_laya_agent,
)

chat_llm = get_llm("CHAT_LLM_MODEL", DEFAULT_CONFIG.chat_model_id, temperature=DEFAULT_CONFIG.chat_temperature)

from core.routing.layer2.heuristics import (
    is_file_operation_query,
    is_workstation_setup_query,
    is_document_inquiry_query,
    filter_setup_tools,
    build_contextual_rag_query,
)
_filter_setup_tools = filter_setup_tools
_build_contextual_rag_query = build_contextual_rag_query

from core.routing.layer2.nodes.retrieval_nodes import (
    document_retrieval_node,
    tool_retrieval_node,
)
from core.routing.layer2.nodes.summary_nodes import summarize_conversation_node
from core.routing.layer2.nodes.memory_nodes import (
    memory_retrieval_node,
    memory_extraction_node,
)
from core.routing.layer2.nodes.routing_nodes import (
    decide_after_tool_retrieval,
    route_query,
    decide_next_step,
    decide_discovery_step,
)
from core.routing.layer2.nodes.mcp_nodes import mcp_discovery_node

__all__ = [
    "get_laya_agent",
    "is_file_operation_query",
    "is_workstation_setup_query",
    "is_document_inquiry_query",
    "_filter_setup_tools",
    "_build_contextual_rag_query",
    "document_retrieval_node",
    "tool_retrieval_node",
    "summarize_conversation_node",
    "memory_retrieval_node",
    "memory_extraction_node",
    "decide_after_tool_retrieval",
    "route_query",
    "decide_next_step",
    "mcp_discovery_node",
    "decide_discovery_step",
    "tool_rag_registry",
    "long_term_memory",
    "chat_llm",
]
