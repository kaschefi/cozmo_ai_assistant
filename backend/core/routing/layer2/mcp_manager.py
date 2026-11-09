# backend/core/routing/layer2/mcp_manager.py
import os
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import sys
import json
import re
import asyncio
import threading
import time
import atexit
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from contextlib import AsyncExitStack

from core.routing.layer2.tool_vector_db import tool_rag_registry

def get_project_root() -> str:
    """Returns the absolute path to MoKa's root workspace directory."""
    cur = os.path.abspath(os.path.dirname(__file__))
    for _ in range(6):
        if os.path.exists(os.path.join(cur, "backend")) and (
            os.path.exists(os.path.join(cur, "frontend")) or os.path.exists(os.path.join(cur, ".git"))
        ):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(os.getcwd())

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = Any
    StdioServerParameters = Any


@dataclass
class ActiveMCPServer:
    pack_id: str
    display_name: str
    session: Any
    exit_stack: AsyncExitStack
    tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    connected_at: float = field(default_factory=time.time)


class MCPClientManager:
    """
    Thread-safe, persistent singleton manager for Model Context Protocol (MCP) clients.
    Maintains persistent stdio subprocesses across multiple LangGraph turns via a
    dedicated background event loop thread.
    """
    _instance: Optional["MCPClientManager"] = None
    _singleton_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super(MCPClientManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._servers: Dict[str, ActiveMCPServer] = {}
        self._lock = threading.RLock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

        # Catalog path resolution
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        self._catalog_path = os.path.join(backend_dir, "data", "mcp_catalog.json")

        self._initialized = True
        atexit.register(self.shutdown)

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._loop is None or not self._loop.is_running():
                self._loop = asyncio.new_event_loop()
                self._loop_thread = threading.Thread(
                    target=self._run_background_loop,
                    name="MCPClientManagerLoop",
                    daemon=True
                )
                self._loop_thread.start()
            return self._loop

    def _run_background_loop(self):
        if self._loop:
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()

    def shutdown(self):
        with self._lock:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
                self._loop = None
                self._loop_thread = None

    def get_catalog(self) -> Dict[str, Any]:
        """Loads and returns the catalog configuration from disk."""
        if not os.path.exists(self._catalog_path):
            return {}
        try:
            with open(self._catalog_path, "r", encoding="utf-8") as f:
                return json.load(f).get("servers", {})
        except Exception as e:
            print(f"[MCPClientManager Error] Failed to read MCP catalog: {e}")
            return {}

    def get_server_config(self, pack_id: str) -> Optional[Dict[str, Any]]:
        catalog = self.get_catalog()
        return catalog.get(pack_id)

    def is_server_connected(self, pack_id: str) -> bool:
        with self._lock:
            return pack_id in self._servers

    def get_active_pack_ids(self) -> List[str]:
        with self._lock:
            return list(self._servers.keys())

    # --- Connection Management ---

    async def _connect_server_async(self, pack_id: str) -> Dict[str, Any]:
        with self._lock:
            if pack_id in self._servers:
                return {
                    "status": "already_connected",
                    "pack_id": pack_id,
                    "tools_count": len(self._servers[pack_id].tools)
                }

        config = self.get_server_config(pack_id)
        if not config:
            raise ValueError(f"Unknown MCP server pack_id: '{pack_id}'. Not found in catalog.")

        display_name = config.get("display_name", pack_id)
        cmd = config.get("command", "npx")
        raw_args = config.get("args", [])
        # Workspace Sandboxing: Resolve '.' strictly to the project root directory. Do NOT expand '~'.
        project_root = get_project_root()
        args = []
        for a in raw_args:
            if a == ".":
                args.append(project_root)
            else:
                args.append(a)
        env_vars = os.environ.copy()

        # Check required env vars
        missing_vars = [v for v in config.get("env_vars", []) if not os.getenv(v)]
        if missing_vars:
            print(f"[MCPClientManager Warning] Server '{pack_id}' requires missing env vars: {missing_vars}")

        # Construct spawn arguments for Windows compatibility
        extra_spawn_args = {"shell": True} if sys.platform == "win32" else {}

        if not MCP_AVAILABLE:
            raise RuntimeError("mcp Python SDK is not installed. Please install 'mcp' package.")

        server_params = StdioServerParameters(
            command=cmd,
            args=args,
            env=env_vars,
            extra_spawn_args=extra_spawn_args
        )

        exit_stack = AsyncExitStack()
        try:
            read_stream, write_stream = await exit_stack.enter_async_context(stdio_client(server_params))
            session = await exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()

            # Query available tools
            tools_response = await session.list_tools()
            tools_list = getattr(tools_response, "tools", [])

            # Parse destructive heuristics
            destructive_regex = config.get("destructive_regex", "")
            default_destructive = set(config.get("default_destructive_tools", []))

            parsed_tools: Dict[str, Dict[str, Any]] = {}
            tools_for_vector_db: List[Dict[str, Any]] = []

            for tool in tools_list:
                t_name = tool.name
                t_desc = tool.description or f"Tool {t_name} from {display_name}"
                schema = tool.inputSchema if hasattr(tool, "inputSchema") else {}

                is_mutating = (t_name in default_destructive) or bool(
                    destructive_regex and re.search(destructive_regex, t_name, re.IGNORECASE)
                )

                tool_dict = {
                    "name": t_name,
                    "description": t_desc,
                    "inputSchema": schema,
                    "is_mutating": is_mutating,
                    "server_pack_id": pack_id
                }
                parsed_tools[t_name] = tool_dict
                tools_for_vector_db.append(tool_dict)

            active_server = ActiveMCPServer(
                pack_id=pack_id,
                display_name=display_name,
                session=session,
                exit_stack=exit_stack,
                tools=parsed_tools
            )

            with self._lock:
                self._servers[pack_id] = active_server

            # Dynamically index granular active tools into FAISS and retire dormant stub
            tool_rag_registry.register_mcp_tools_runtime(pack_id=pack_id, mcp_tools=tools_for_vector_db)

            print(f"[MCPClientManager] Connected '{display_name}' ({pack_id}) with {len(parsed_tools)} tools.")
            return {
                "status": "connected",
                "pack_id": pack_id,
                "display_name": display_name,
                "tools_count": len(parsed_tools),
                "tools": list(parsed_tools.keys())
            }

        except Exception as e:
            await exit_stack.aclose()
            print(f"[MCPClientManager Error] Failed connecting to MCP '{pack_id}': {e}")
            raise e

    def connect_server_sync(self, pack_id: str) -> Dict[str, Any]:
        """Synchronously blocks until the MCP server connects and tools are indexed."""
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(self._connect_server_async(pack_id), loop)
        return future.result(timeout=60)

    async def _disconnect_server_async(self, pack_id: str) -> bool:
        with self._lock:
            server = self._servers.pop(pack_id, None)

        if not server:
            return False

        try:
            await server.exit_stack.aclose()
            # Remove from vector registry and re-instate dormant stub
            tool_rag_registry.remove_mcp_tools_runtime(pack_id=pack_id, reinstate_dormant=True)
            print(f"[MCPClientManager] Disconnected server '{pack_id}'.")
            return True
        except Exception as e:
            print(f"[MCPClientManager Warning] Error during shutdown of '{pack_id}': {e}")
            return False

    def disconnect_server_sync(self, pack_id: str) -> bool:
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(self._disconnect_server_async(pack_id), loop)
        return future.result(timeout=30)

    # --- Tool Execution ---

    async def _call_mcp_tool_async(self, pack_id: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        with self._lock:
            server = self._servers.get(pack_id)

        if not server:
            raise ValueError(f"MCP server '{pack_id}' is not connected.")

        try:
            response = await server.session.call_tool(name=tool_name, arguments=arguments)
            text_contents = [
                c.text for c in getattr(response, "content", [])
                if hasattr(c, "text")
            ]
            return "\n".join(text_contents) if text_contents else "Tool executed successfully with no text output."
        except Exception as e:
            print(f"[MCPClientManager Error] Tool '{tool_name}' failed on '{pack_id}': {e}")
            return f"Error executing tool '{tool_name}' on server '{pack_id}': {e}"

    def call_mcp_tool_sync(self, pack_id: str, tool_name: str, arguments: Dict[str, Any]) -> str:
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(
            self._call_mcp_tool_async(pack_id, tool_name, arguments),
            loop
        )
        return future.result(timeout=60)

    def get_status(self) -> Dict[str, Any]:
        """Provides status snapshot for API telemetry and cognitive badges."""
        catalog = self.get_catalog()
        with self._lock:
            active_info = {
                pid: {
                    "pack_id": pid,
                    "display_name": s.display_name,
                    "description": catalog.get(pid, {}).get("description", ""),
                    "tools_count": len(s.tools),
                    "tools": [
                        {
                            "name": t.get("name"),
                            "description": t.get("description", ""),
                            "is_mutating": t.get("is_mutating", False)
                        }
                        for t in s.tools.values()
                    ],
                    "tool_names": list(s.tools.keys()),
                    "connected_at": s.connected_at
                }
                for pid, s in self._servers.items()
            }
            dormant_info = {
                pid: {
                    "pack_id": pid,
                    "display_name": cfg.get("display_name", pid),
                    "description": cfg.get("description", ""),
                    "command": cfg.get("command", ""),
                    "env_vars": cfg.get("env_vars", [])
                }
                for pid, cfg in catalog.items()
                if pid not in self._servers
            }

        return {
            "active_servers": active_info,
            "dormant_servers": dormant_info,
            "total_active_servers": len(active_info),
            "total_dormant_servers": len(dormant_info),
            "total_indexed_tools": len(tool_rag_registry._tools_source)
        }


mcp_manager = MCPClientManager()
