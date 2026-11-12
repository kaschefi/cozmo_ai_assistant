# core/routing/layer2/nodes/mcp_nodes.py
from typing import Dict, Any
from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from core.routing.layer2.mcp_manager import mcp_manager
from schemas.request_models import AgentState


def mcp_discovery_node(state: AgentState) -> Dict[str, Any]:
    """
    Gate 1 HITL checkpoint:
    Pauses execution and asks the user whether they want MoKa to add the new tool/MCP pack.
    """
    pack_id = state.get("next_route", "")
    catalog = mcp_manager.get_catalog()
    server_cfg = catalog.get(pack_id, {})
    display_name = server_cfg.get("display_name", pack_id)
    description = server_cfg.get("description", "")

    # Request human confirmation to add the tool
    decision = interrupt({
        "type": "hitl_interrupt",
        "interrupt_type": "mcp_discovery",
        "server_pack_id": pack_id,
        "display_name": display_name,
        "description": description,
        "message": f"I need the '{display_name}' tool to help you with that. Would you like me to add it so I can use it?",
    })

    approved = False
    if isinstance(decision, dict):
        approved = bool(decision.get("approved"))
    elif isinstance(decision, bool):
        approved = decision
    elif isinstance(decision, str):
        approved = decision.strip().lower() in ("yes", "y", "true", "approve", "1")

    if approved:
        print(f"[mcp_discovery_node] User APPROVED adding '{display_name}'. Connecting & ingesting tools...")
        try:
            connect_res = mcp_manager.connect_server_sync(pack_id)
            tools_count = connect_res.get("tools_count", 0)
            print(f"[mcp_discovery_node] Successfully added {tools_count} tools from '{display_name}'.")
            return {
                "resumed_from_interrupt": True,
                "mcp_active_servers": mcp_manager.get_active_pack_ids(),
                "next_route": "re_evaluate",
            }
        except Exception as e:
            print(f"[mcp_discovery_node Error] Failed to connect '{pack_id}': {e}")
            return {
                "resumed_from_interrupt": True,
                "messages": [AIMessage(content=f"I tried to add '{display_name}', but encountered an issue: {e}")],
                "next_route": "none",
            }
    else:
        print(f"[mcp_discovery_node] User DECLINED adding '{display_name}'.")
        return {
            "resumed_from_interrupt": True,
            "messages": [AIMessage(content=f"Understood! I won't add '{display_name}'. Let me know if you need help with anything else.")],
            "next_route": "none",
        }

