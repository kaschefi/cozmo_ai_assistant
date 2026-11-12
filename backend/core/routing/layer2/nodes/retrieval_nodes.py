# core/routing/layer2/nodes/retrieval_nodes.py
import sys
from typing import Dict, Any, List

from core.routing.layer2.config import DEFAULT_CONFIG
from core.routing.layer2.heuristics import (
    is_file_operation_query,
    filter_setup_tools,
    build_contextual_rag_query,
)
from schemas.request_models import AgentState

try:
    from test.routers.tools import TOOL_TO_DOMAIN
except Exception:
    TOOL_TO_DOMAIN = {}


def _get_active_registry():
    gn = sys.modules.get("core.routing.layer2.graph_nodes")
    if gn and hasattr(gn, "tool_rag_registry"):
        return gn.tool_rag_registry
    from core.routing.layer2.tool_vector_db import tool_rag_registry
    return tool_rag_registry


def document_retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    Post-Route Grounded Context Gathering on the conversational/QA branch:
    Queries the Semantic ETL Pipeline Knowledge Base for relevant passages, requirements,
    and citations from uploaded documents (PDF, DOCX, TXT, MD).
    Stores retrieved context blocks in state['retrieved_documents'].
    """
    messages = state.get("messages", [])
    if not messages:
        return {"retrieved_documents": []}

    try:
        from actions.digital.semantic_etl_client import retrieve_document_context, is_semantic_etl_healthy
        if not is_semantic_etl_healthy():
            return {"retrieved_documents": []}

        rag_query = build_contextual_rag_query(messages)
        namespace = (state.get("document_namespace") or "documents").strip() or "documents"
        res = retrieve_document_context(rag_query, namespace=namespace)
        sources = res.get("sources", [])
        if sources:
            print(f"[document_retrieval_node] Injected {len(sources)} grounded document excerpts into state (namespace='{namespace}').")
        return {"retrieved_documents": sources}
    except Exception as e:
        print(f"[document_retrieval_node Error]: Context retrieval warning: {e}")
        return {"retrieved_documents": []}


def tool_retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    RAG LAYER STEP 1: Two-Layer Top-K Tool Retrieval.
    Programmatically query our tool database vector space with distance thresholding.
    If no tools pass or the nearest tool is a weak match (> 1.10), fall back to conversational 'none'.
    """
    last_message = state["messages"][-1].content
    if state.get("rag_only"):
        return {"active_tools": []}

    # If the user is asking to access external system folders outside MoKa's workspace,
    # bypass tool retrieval so the assistant handles it directly via chat_node without triggering HITL
    from core.routing.layer2.worker_nodes import is_external_system_path_query
    if is_external_system_path_query(last_message):
        return {"active_tools": []}

    registry = _get_active_registry()

    if registry.db is None or not any(d.metadata.get("source_type") == "mcp_dormant" for d in registry._tools_source):
        registry.load_dormant_catalog()
        registry.build_index()

    # Step 2 from Two-Layer Top-K: probe_k = 8, distance_threshold = 1.15
    matched_tools = registry.search_relevant_tools(
        last_message, k=DEFAULT_CONFIG.probe_k, distance_threshold=DEFAULT_CONFIG.distance_threshold
    )

    # If no tools pass or nearest tool is a weak match (> 1.10), fall back to conversational "none"
    if not matched_tools or (matched_tools and matched_tools[0].get("score", 0.0) > DEFAULT_CONFIG.weak_match_threshold):
        return {"active_tools": []}

    # 1. Filter out workstation app launchers unless user explicitly issued a setup command
    matched_tools = filter_setup_tools(matched_tools, last_message, DEFAULT_CONFIG.setup_exclusion_names)
    if not matched_tools:
        return {"active_tools": []}

    top_score = matched_tools[0].get("score", 0.0)
    top_tool = matched_tools[0]["name"]
    primary_domain = TOOL_TO_DOMAIN.get(top_tool)

    # Hierarchical Domain Selection (pruning cross-namespace lexical distractors):
    top3_domains = [TOOL_TO_DOMAIN.get(m["name"]) for m in matched_tools[:3]]
    if top_score <= DEFAULT_CONFIG.top_domain_score_threshold or top3_domains.count(primary_domain) >= 2:
        allowed_domains = {primary_domain}
    else:
        allowed_domains = {primary_domain}
        for m in matched_tools[1:4]:
            if m.get("score", 0.0) <= top_score + DEFAULT_CONFIG.domain_margin:
                d = TOOL_TO_DOMAIN.get(m["name"])
                if d:
                    allowed_domains.add(d)

    active_tools = [
        t for t in matched_tools
        if (TOOL_TO_DOMAIN.get(t["name"]) in allowed_domains or not allowed_domains)
        and t.get("score", 0.0) <= top_score + DEFAULT_CONFIG.tool_score_margin
    ]
    if not active_tools:
        active_tools = [matched_tools[0]]

    # Bound candidates to at most max_candidate_tools to prevent ModernBERT softmax logit collapse
    active_tools = active_tools[:DEFAULT_CONFIG.max_candidate_tools]

    # If the user is asking for a file operation, guarantee that filesystem tools or dormant pack are present
    if is_file_operation_query(last_message):
        has_fs = any(
            t.get("name") == "mcp_pack_filesystem" or t.get("server_pack_id") == "mcp_pack_filesystem"
            for t in active_tools
        )
        if not has_fs:
            fs_doc = next(
                (d for d in registry._tools_source if d.metadata.get("tool_name") == "mcp_pack_filesystem" or d.metadata.get("server_pack_id") == "mcp_pack_filesystem"),
                None
            )
            if fs_doc:
                name = fs_doc.metadata["tool_name"]
                active_tools.insert(0, {
                    "name": name,
                    "description": fs_doc.page_content,
                    "score": 0.5,
                    "source_type": fs_doc.metadata.get("source_type", "mcp_dormant"),
                    "server_pack_id": fs_doc.metadata.get("server_pack_id", "mcp_pack_filesystem"),
                    "input_schema": fs_doc.metadata.get("input_schema", {}),
                    "is_mutating": fs_doc.metadata.get("is_mutating", False)
                })
                active_tools = active_tools[:DEFAULT_CONFIG.max_candidate_tools]

    return {"active_tools": active_tools}
