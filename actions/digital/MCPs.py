# actions/digital/mcp_tavily.py
import os
import asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Load variables from your local .env file
load_dotenv()


async def fetch_tavily_search(query: str) -> str:
    """
    Connects to Tavily's official MCP server using npx and triggers
    a highly optimized AI web search.
    """
    # Configure the official Tavily MCP package parameters
    env_vars = os.environ.copy()
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "tavily-mcp@latest"],
        env=env_vars,
        extra_spawn_args={"shell": True}
    )

    try:
        # Establish the stdio pipe connection
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize protocol handshake
                await session.initialize()

                # Execute Tavily's native web search tool
                response = await session.call_tool(
                    name="tavily_search",
                    arguments={
                        "query": query,
                        "search_depth": "advanced",  # or "advanced"
                        "max_results": 5
                    }
                )

                # Extract text payloads from the server response
                text_contents = [
                    content.text for content in response.content
                    if hasattr(content, 'text')
                ]

                return "\n".join(text_contents) if text_contents else "No search data returned."

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error executing Tavily MCP Search: {e}")
        return f"I had an issue searching via Tavily MCP: {e}"


def call_tavily_mcp_search(query: str) -> str:
    """Synchronous wrapper"""
    return asyncio.run(fetch_tavily_search(query))
