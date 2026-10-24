# backend/test/digital/routers/tools/registry.py
"""
Aggregates every namespace into one Layer 1 Tool RAG spec list and Master Tool Dictionary.
Total: 100 unique tools. code_executor_node contributes 5 vectors but counts as 1 tool.
"""

from typing import Dict, List, Optional

from .cognitive import COGNITIVE_TOOLS, COGNITIVE_RAG_SPECS, COGNITIVE_NAMESPACE
from .desktop import DESKTOP_TOOLS, DESKTOP_RAG_SPECS, DESKTOP_NAMESPACE
from .robot import ROBOT_TOOLS, ROBOT_RAG_SPECS, ROBOT_NAMESPACE
from .media import MEDIA_TOOLS, MEDIA_RAG_SPECS, MEDIA_NAMESPACE
from .smart_home import SMART_HOME_TOOLS, SMART_HOME_RAG_SPECS, SMART_HOME_NAMESPACE
from .companion import COMPANION_TOOLS, COMPANION_RAG_SPECS, COMPANION_NAMESPACE
from .comms import COMMS_TOOLS, COMMS_RAG_SPECS, COMMS_NAMESPACE
from .productivity import PRODUCTIVITY_TOOLS, PRODUCTIVITY_RAG_SPECS, PRODUCTIVITY_NAMESPACE

# -----------------------------------------------------------------------------
# Master Dictionary of all 100 Unique Tools
# -----------------------------------------------------------------------------
ALL_TOOLS_DICT: Dict[str, str] = {
    **ROBOT_TOOLS,
    **DESKTOP_TOOLS,
    **COGNITIVE_TOOLS,
    **MEDIA_TOOLS,
    **SMART_HOME_TOOLS,
    **COMPANION_TOOLS,
    **COMMS_TOOLS,
    **PRODUCTIVITY_TOOLS,
}

# -----------------------------------------------------------------------------
# Master RAG Registry Specifications (104 vector documents across 100 tools)
# -----------------------------------------------------------------------------
ALL_RAG_SPECS: List[Dict[str, str]] = (
    ROBOT_RAG_SPECS
    + DESKTOP_RAG_SPECS
    + COGNITIVE_RAG_SPECS
    + MEDIA_RAG_SPECS
    + SMART_HOME_RAG_SPECS
    + COMPANION_RAG_SPECS
    + COMMS_RAG_SPECS
    + PRODUCTIVITY_RAG_SPECS
)


def unique_tool_names(specs: List[Dict[str, str]] = ALL_RAG_SPECS) -> List[str]:
    """Returns sorted list of all unique tool names in the registry."""
    return sorted({s["name"] for s in specs})


def get_specs(limit: Optional[int] = None) -> List[Dict[str, str]]:
    """Return RAG specs for the first `limit` unique tools (for 18/20/30/50/100 scaling runs)."""
    if limit is None or limit >= len(ALL_TOOLS_DICT):
        return ALL_RAG_SPECS
    keep = set(unique_tool_names()[:limit])
    return [s for s in ALL_RAG_SPECS if s["name"] in keep]


def get_tools(limit: Optional[int] = None) -> Dict[str, str]:
    """Return tool dictionary for the first `limit` unique tools."""
    if limit is None or limit >= len(ALL_TOOLS_DICT):
        return dict(ALL_TOOLS_DICT)
    keep = set(unique_tool_names()[:limit])
    return {k: v for k, v in ALL_TOOLS_DICT.items() if k in keep}


if __name__ == "__main__":
    names = unique_tool_names()
    print(f"{len(names)} unique tools, {len(ALL_RAG_SPECS)} vector documents")
    assert len(names) == 100, f"expected 100 tools, got {len(names)}"
    assert len(ALL_TOOLS_DICT) == 100, f"expected 100 tools dict, got {len(ALL_TOOLS_DICT)}"
