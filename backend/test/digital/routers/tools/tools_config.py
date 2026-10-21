# backend/test/digital/routers/tools/tools_config.py
"""
Aggregated Tools Configuration for Router Benchmarking.

Imports partitioned tool definitions from their respective domain namespaces:
- robot.* (Physical chassis kinematics, head, lift, docking, scanning)
- desktop.* (Workstation presets, local apps, OS utilities)
- cognitive.* (Search, calendar, math sandbox, weather, tasks)
- media.* (Spotify, YouTube, media controls)
- smart_home.* (IoT lights, plugs, thermostats - placeholder)

Gathers all definitions into unified registries (TOOLS_18, TOOLS_15, TOOL_RAG_REGISTRY_SPECS)
to provide a scalable foundation for 20 -> 100+ tools.
"""

from typing import Dict, Any, List

# Import domain namespaces
from test.digital.routers.tools.robot import (
    ROBOT_NAMESPACE,
    ROBOT_TOOLS,
    ROBOT_RAG_SPECS,
)
from test.digital.routers.tools.desktop import (
    DESKTOP_NAMESPACE,
    DESKTOP_TOOLS,
    DESKTOP_RAG_SPECS,
)
from test.digital.routers.tools.cognitive import (
    COGNITIVE_NAMESPACE,
    COGNITIVE_TOOLS,
    COGNITIVE_RAG_SPECS,
    CODE_EXECUTOR_DIMENSIONS,
)
from test.digital.routers.tools.media import (
    MEDIA_NAMESPACE,
    MEDIA_TOOLS,
    MEDIA_RAG_SPECS,
    PLANNED_MEDIA_TOOLS,
)
from test.digital.routers.tools.smart_home import (
    SMART_HOME_NAMESPACE,
    SMART_HOME_TOOLS,
    SMART_HOME_RAG_SPECS,
)

# -----------------------------------------------------------------------------
# Conversational Fallback Channel
# -----------------------------------------------------------------------------
FALLBACK_ROUTE: Dict[str, str] = {
    "none": (
        "Core conversational channel. Use for casual chat, greetings, social pleasantries, asking about "
        "identity/personality, sharing personal facts or hobbies, jokes, philosophical discussion, or small talk."
    ),
}

# -----------------------------------------------------------------------------
# Unified 18 Core Active Tools (+ 'none' fallback = 19 routes total)
# -----------------------------------------------------------------------------
TOOLS_18: Dict[str, str] = {
    **ROBOT_TOOLS,
    **DESKTOP_TOOLS,
    **COGNITIVE_TOOLS,
    **MEDIA_TOOLS,
    **FALLBACK_ROUTE,
}

# Master alias for all active tools in the system
TOOLS_ALL: Dict[str, str] = TOOLS_18

# Backward-compatible 15 Core Tools subset (used in initial WP2 48-case benchmark)
TOOLS_15: Dict[str, str] = {
    k: v for k, v in TOOLS_18.items()
    if k not in ("arc_sweep", "code_executor_node", "todolist_node")
}

# -----------------------------------------------------------------------------
# Hierarchical Domain Namespacing (Phase 2 Scaling Foundation)
# Maps domain keys (robot, desktop, cognitive, media, smart_home) to their tool subsets
# -----------------------------------------------------------------------------
TOOL_NAMESPACES: Dict[str, Dict[str, str]] = {
    ROBOT_NAMESPACE: ROBOT_TOOLS,
    DESKTOP_NAMESPACE: DESKTOP_TOOLS,
    COGNITIVE_NAMESPACE: COGNITIVE_TOOLS,
    MEDIA_NAMESPACE: MEDIA_TOOLS,
    SMART_HOME_NAMESPACE: SMART_HOME_TOOLS,
}

# -----------------------------------------------------------------------------
# Layer 1 Tool RAG Indexing Specifications (Multi-Document Registry)
# Gathers all raw documents for FAISS indexing across all namespaces.
# Multi-faceted tools (e.g. code_executor_node) contain multiple short dimensional schemas.
# -----------------------------------------------------------------------------
TOOL_RAG_REGISTRY_SPECS: List[Dict[str, str]] = (
    ROBOT_RAG_SPECS
    + DESKTOP_RAG_SPECS
    + COGNITIVE_RAG_SPECS
    + MEDIA_RAG_SPECS
    + SMART_HOME_RAG_SPECS
)


def build_laya_questions(tools_dict: Dict[str, str] = TOOLS_18) -> Dict[str, Any]:
    """
    Builds the typed choice question dictionary required by Laya.
    Defaults to all 18 tools + 'none', but accepts any candidate subset (e.g. Top-K from FAISS).
    """
    return {
        "tool_selection": {
            "type": "choice",
            "instructions": (
                "Select the appropriate tool or service to handle the user's request, question, or command. "
                "Use 'web_search_node' whenever the user wants to look up information, search the web, check company market data, sports results, or news. "
                "Select 'none' only if the user is simply chatting, greeting, sharing personal facts, or making casual small talk."
            ),
            "criteria": tools_dict,
        }
    }


def register_all_tools_to_rag(registry=None):
    """
    Helper to register all system tools across all namespaces into the Layer 1 FAISS ToolVectorRegistry.
    Uses multi-dimensional short explanations for code_executor_node so queries
    for arithmetic, logic, sorting, date parsing, or word reversal match with high similarity.
    """
    if registry is None:
        from core.routing.layer2.tool_vector_db import tool_rag_registry
        registry = tool_rag_registry

    for spec in TOOL_RAG_REGISTRY_SPECS:
        registry.register_tool_schema(name=spec["name"], description=spec["description"])
