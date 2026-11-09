# actions/digital/MCPs.py
import os
import asyncio
from dotenv import load_dotenv

from core.routing.layer2.mcp_manager import mcp_manager

# Load variables from your local .env file
load_dotenv()


async def fetch_tavily_search(query: str) -> str:
    """
    Connects to Tavily's official MCP server and executes an AI web search
    via the unified MCPClientManager.
    """
    pack_id = "mcp_pack_tavily"
    try:
        if not mcp_manager.is_server_connected(pack_id):
            mcp_manager.connect_server_sync(pack_id)

        return mcp_manager.call_mcp_tool_sync(
            pack_id=pack_id,
            tool_name="tavily_search",
            arguments={
                "query": query,
                "search_depth": "advanced",
                "max_results": 5
            }
        )
    except Exception as e:
        print(f"Error executing Tavily MCP Search: {e}")
        return f"I had an issue searching via Tavily MCP: {e}"


def call_tavily_mcp_search(query: str) -> str:
    """Synchronous wrapper"""
    return asyncio.run(fetch_tavily_search(query))
