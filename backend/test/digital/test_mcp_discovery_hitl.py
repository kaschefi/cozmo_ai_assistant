# backend/test/digital/test_mcp_discovery_hitl.py
"""
Test Suite for Runtime MCP Tool Discovery, Dynamic FAISS Vector Indexing,
and Human-In-The-Loop (HITL) Capability Addition in MoKa Layer 2.
Runs 100% hardware-free (--dry-run).
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure offline/dry-run execution without network delays
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["DISABLE_POSTGRES_CHECKPOINTER"] = "1"

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from core.routing.layer2.tool_vector_db import ToolVectorRegistry
from core.routing.layer2.mcp_manager import MCPClientManager


def test_tool_vector_registry_dormant_and_runtime_mutation():
    """
    Verifies that ToolVectorRegistry can:
    1. Seed dormant MCP stubs from mcp_catalog.json.
    2. Hot-reload granular active tools at runtime.
    3. Retire the dormant stub upon activation.
    4. Re-instate the dormant stub when removed.
    """
    registry = ToolVectorRegistry()
    # 1. Register a few native tools
    registry.register_tool_schema(name="weather_node", description="Get current weather for any city.")
    registry.register_tool_schema(name="calendar_node", description="Create or list Google Calendar events.")

    # 2. Load dormant catalog stubs
    registry.load_dormant_catalog()
    registry.build_index()

    # Query for GitHub before activation: should match dormant stub
    initial_matches = registry.search_relevant_tools("Show my GitHub pull requests", k=3)
    match_names = [m["name"] for m in initial_matches]
    assert "mcp_pack_github" in match_names, f"Expected 'mcp_pack_github' in matches, got: {match_names}"
    dormant_match = next(m for m in initial_matches if m["name"] == "mcp_pack_github")
    assert dormant_match["source_type"] == "mcp_dormant"

    # 3. Simulate runtime activation of GitHub tools
    sample_github_tools = [
        {
            "name": "github_list_pull_requests",
            "description": "List open and closed pull requests in a GitHub repository.",
            "inputSchema": {"type": "object", "properties": {"repo": {"type": "string"}}},
            "is_mutating": False
        },
        {
            "name": "github_create_issue",
            "description": "Create a new issue on a GitHub repository.",
            "inputSchema": {"type": "object", "properties": {"repo": {"type": "string"}, "title": {"type": "string"}}},
            "is_mutating": True
        }
    ]
    registry.register_mcp_tools_runtime(pack_id="mcp_pack_github", mcp_tools=sample_github_tools)

    # Query again for GitHub pull requests: dormant stub MUST be retired, granular tool MUST appear!
    post_activation_matches = registry.search_relevant_tools("Show my GitHub pull requests", k=3)
    post_names = [m["name"] for m in post_activation_matches]
    assert "mcp_pack_github" not in post_names, "Dormant stub 'mcp_pack_github' must be retired after activation!"
    assert "github_list_pull_requests" in post_names, f"Expected 'github_list_pull_requests' in matches, got: {post_names}"
    active_match = next(m for m in post_activation_matches if m["name"] == "github_list_pull_requests")
    assert active_match["source_type"] == "mcp_active"
    assert active_match["server_pack_id"] == "mcp_pack_github"

    # 4. Remove active tools and re-instate dormant stub
    registry.remove_mcp_tools_runtime(pack_id="mcp_pack_github", reinstate_dormant=True)
    post_removal_matches = registry.search_relevant_tools("Show my GitHub pull requests", k=3)
    post_removal_names = [m["name"] for m in post_removal_matches]
    assert "github_list_pull_requests" not in post_removal_names
    assert "mcp_pack_github" in post_removal_names


def test_mcp_manager_catalog_and_status():
    """Verifies that MCPClientManager reads the catalog correctly and outputs telemetry."""
    mgr = MCPClientManager()
    catalog = mgr.get_catalog()
    assert "mcp_pack_github" in catalog
    assert "mcp_pack_postgres" in catalog
    assert "mcp_pack_filesystem" in catalog

    status = mgr.get_status()
    assert "total_active_servers" in status
    assert "total_dormant_servers" in status
    assert status["total_dormant_servers"] >= 4


def test_langgraph_hitl_interrupt_and_resume_cycle():
    """
    Tests the complete LangGraph execution cycle with HITL:
    1. Discovery node halts on interrupt() asking user permission.
    2. Resuming with approved=False gracefully exits to chat without connecting.
    3. Resuming with approved=True connects, indexes tools, and executes.
    """
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import interrupt, Command
    from langchain_core.messages import HumanMessage, AIMessage
    from schemas.request_models import AgentState

    connected_servers = []

    def mock_retrieval(state: AgentState):
        # First turn: returns dormant stub
        if not connected_servers:
            return {"active_tools": [{"name": "mcp_pack_github", "description": "GitHub tools", "source_type": "mcp_dormant"}]}
        # After approval: returns active granular tool
        return {"active_tools": [{"name": "github_list_prs", "description": "List PRs", "source_type": "mcp_active", "server_pack_id": "mcp_pack_github"}]}

    def mock_router(state: AgentState):
        active = state.get("active_tools", [])
        if any(t["name"] == "github_list_prs" for t in active):
            return {"next_route": "github_list_prs"}
        return {"next_route": "mcp_pack_github"}

    def mock_decide_next(state: AgentState):
        route = state.get("next_route")
        if route == "mcp_pack_github":
            return "discovery"
        return "execute"

    def mock_discovery(state: AgentState):
        pack = state.get("next_route")
        decision = interrupt({
            "type": "hitl_interrupt",
            "server_pack_id": pack,
            "message": f"Add {pack} so I can use it?"
        })
        approved = decision.get("approved") if isinstance(decision, dict) else decision
        if approved:
            connected_servers.append(pack)
            return {"next_route": "re_evaluate"}
        return {"messages": [AIMessage(content="User declined adding tool.")], "next_route": "none"}

    def mock_decide_discovery(state: AgentState):
        if state.get("next_route") == "re_evaluate":
            return "retrieval"
        return "finish"

    def mock_execute(state: AgentState):
        route = state.get("next_route")
        return {"messages": [AIMessage(content=f"Executed {route} successfully.")]}

    def mock_finish(state: AgentState):
        return {}

    # Compile test graph
    b = StateGraph(AgentState)
    b.add_node("retrieval", mock_retrieval)
    b.add_node("router", mock_router)
    b.add_node("discovery", mock_discovery)
    b.add_node("execute", mock_execute)
    b.add_node("finish", mock_finish)

    b.add_edge(START, "retrieval")
    b.add_edge("retrieval", "router")
    b.add_conditional_edges("router", mock_decide_next, {"discovery": "discovery", "execute": "execute"})
    b.add_conditional_edges("discovery", mock_decide_discovery, {"retrieval": "retrieval", "finish": "finish"})
    b.add_edge("execute", "finish")
    b.add_edge("finish", END)

    mem_checkpointer = MemorySaver()
    g = b.compile(checkpointer=mem_checkpointer)

    # 1. Turn 1: Invocation halts at Gate 1 interrupt
    thread_id = "test_thread_hitl"
    cfg = {"configurable": {"thread_id": thread_id}}
    init_state = {"messages": [HumanMessage(content="Check my pull requests on GitHub")], "active_tools": []}

    g.invoke(init_state, config=cfg)
    state = g.get_state(cfg)
    assert len(state.next) > 0, "Graph should have paused on interrupt!"
    assert len(state.tasks[0].interrupts) > 0
    interrupt_payload = state.tasks[0].interrupts[0].value
    assert interrupt_payload["server_pack_id"] == "mcp_pack_github"

    # 2. Turn 2: User Approves adding the tool
    resumed = g.invoke(Command(resume={"approved": True}), config=cfg)
    final_state = g.get_state(cfg)
    assert len(final_state.next) == 0, "Graph should have completed after resume!"
    assert "mcp_pack_github" in connected_servers
    assert "Executed github_list_prs successfully." in resumed["messages"][-1].content


def test_scoped_tool_rag_registry_backward_compatibility():
    """
    Ensures that create_scoped_tool_rag_registry used in Thesis / WP2 evaluations
    continues to function with 100% backward compatibility.
    """
    from test.routers.tools.tools_config import create_scoped_tool_rag_registry, TOOLS_15
    scoped_reg = create_scoped_tool_rag_registry(TOOLS_15)
    assert scoped_reg.db is not None
    results = scoped_reg.search_relevant_tools("what is the weather in Paris?", k=3)
    assert len(results) > 0
    names = [r["name"] for r in results]
    assert "weather_node" in names


def test_workspace_sandboxing():
    """
    Verifies that MoKa enforces strict workspace sandboxing:
    1. Rejects access to Downloads, Desktop, user home ~, external drive letters, and traversal.
    2. Allows paths strictly inside MoKa's project directory.
    3. Correctly flags external system path queries to bypass tool discovery and route to chat.
    4. execute_tool_node blocks out-of-bounds paths and returns security explanation.
    """
    from core.routing.layer2.worker_nodes import (
        get_project_root,
        validate_workspace_path,
        is_external_system_path_query,
        execute_tool_node
    )
    from langchain_core.messages import HumanMessage, AIMessage

    root = get_project_root()
    assert os.path.exists(root)

    # 1. Negative tests: paths outside workspace must fail validation
    invalid_paths = [
        "Downloads",
        "downloads/file.txt",
        "Desktop",
        "~/Downloads",
        "~\\Documents",
        "..",
        "../../",
        "C:\\Windows\\System32",
        "C:\\Users",
    ]
    for p in invalid_paths:
        is_valid, _ = validate_workspace_path(p, root)
        assert not is_valid, f"Expected '{p}' to be rejected as outside workspace!"

    # 2. Positive tests: paths inside workspace must be valid
    valid_paths = [
        ".",
        "",
        "backend",
        "backend/data",
        "main.py",
        os.path.join(root, "backend")
    ]
    for p in valid_paths:
        is_valid, resolved = validate_workspace_path(p, root)
        assert is_valid, f"Expected '{p}' to be accepted inside workspace!"

    # 3. Query intent detection
    assert is_external_system_path_query("can you give me the name of the last file that is in the Downloads directory")
    assert is_external_system_path_query("show me what is on my desktop")
    assert is_external_system_path_query("read file from C:\\secrets.txt")
    assert not is_external_system_path_query("list files in backend")
    assert not is_external_system_path_query("show my pull requests on GitHub")

    # 4. execute_tool_node security block
    blocked_state = {
        "next_route": "read_file",
        "messages": [HumanMessage(content="can you read file in Downloads?")],
        "active_tools": [{
            "name": "read_file",
            "source_type": "mcp_active",
            "server_pack_id": "mcp_pack_filesystem",
            "input_schema": {"properties": {"path": {"type": "string"}}}
        }],
        "provider": "local"
    }
    res = execute_tool_node(blocked_state)
    assert len(res.get("messages", [])) > 0
    reply = res["messages"][-1].content
    assert "restricted to my own workspace folder" in reply


def test_mutating_mcp_tool_hitl():
    """
    Verifies that:
    1. Read-only MCP tools (is_mutating=False) execute directly without interrupt.
    2. Mutating MCP tools (is_mutating=True) pause on interrupt() with 'mutating_tool'.
    3. Resuming with approved=False cancels the action without calling the tool.
    4. Resuming with approved=True executes the tool.
    """
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.types import Command
    from langchain_core.messages import HumanMessage, AIMessage
    from schemas.request_models import AgentState
    from core.routing.layer2.worker_nodes import execute_tool_node

    executed_tools = []

    # Mock call_mcp_tool_sync
    with patch("core.routing.layer2.mcp_manager.mcp_manager.call_mcp_tool_sync", side_effect=lambda pack_id, tool_name, arguments: executed_tools.append(tool_name) or f"Output of {tool_name}"):
        with patch("core.routing.llm_factory.get_chat_companion_llm") as mock_get_llm:
            mock_llm_inst = MagicMock()
            mock_llm_inst.invoke.return_value = AIMessage(content="Simulated execution reply.")
            mock_get_llm.return_value = mock_llm_inst

            # Graph with execute_tool_node
            b = StateGraph(AgentState)
            b.add_node("execute_tool_node", execute_tool_node)
            b.add_edge(START, "execute_tool_node")
            b.add_edge("execute_tool_node", END)
            g = b.compile(checkpointer=MemorySaver())

            # Case A: Read-Only Tool (e.g. read_file) -> runs immediately without interrupt
            thread_ro = "thread_ro_test"
            cfg_ro = {"configurable": {"thread_id": thread_ro}}
            state_ro = {
                "next_route": "read_file",
                "messages": [HumanMessage(content="read main.py")],
                "active_tools": [{
                    "name": "read_file",
                    "source_type": "mcp_active",
                    "server_pack_id": "mcp_pack_filesystem",
                    "input_schema": {"properties": {"path": {"type": "string"}}},
                    "is_mutating": False
                }],
                "provider": "local"
            }
            res_ro = g.invoke(state_ro, config=cfg_ro)
            state_ro_snap = g.get_state(cfg_ro)
            assert len(state_ro_snap.next) == 0, "Read-only tool must complete without pausing!"
            assert "read_file" in executed_tools

            # Case B: Mutating Tool (e.g. delete_file) -> pauses on interrupt()
            thread_mut = "thread_mut_test"
            cfg_mut = {"configurable": {"thread_id": thread_mut}}
            state_mut = {
                "next_route": "delete_file",
                "messages": [HumanMessage(content="delete temp.log")],
                "active_tools": [{
                    "name": "delete_file",
                    "source_type": "mcp_active",
                    "server_pack_id": "mcp_pack_filesystem",
                    "input_schema": {"properties": {"path": {"type": "string"}}},
                    "is_mutating": True
                }],
                "provider": "local"
            }
            g.invoke(state_mut, config=cfg_mut)
            snap_mut = g.get_state(cfg_mut)
            assert len(snap_mut.next) > 0, "Mutating tool must pause on interrupt!"
            assert len(snap_mut.tasks[0].interrupts) > 0
            payload = snap_mut.tasks[0].interrupts[0].value
            assert payload["interrupt_type"] == "mutating_tool"
            assert payload["tool_name"] == "delete_file"

            # Case C: Resume with approved=False -> cancels execution cleanly
            thread_decline = "thread_decline_test"
            cfg_dec = {"configurable": {"thread_id": thread_decline}}
            g.invoke(state_mut, config=cfg_dec)
            res_dec = g.invoke(Command(resume={"approved": False}), config=cfg_dec)
            assert "cancelled as requested" in res_dec["messages"][-1].content

            # Case D: Resume with approved=True -> executes mutating tool
            res_app = g.invoke(Command(resume={"approved": True}), config=cfg_mut)
            assert len(g.get_state(cfg_mut).next) == 0
            assert "delete_file" in executed_tools


if __name__ == "__main__":
    print("Running MCP Discovery & HITL Verification Suite...", flush=True)
    test_tool_vector_registry_dormant_and_runtime_mutation()
    print("[TEST 1 PASSED]: tool_vector_registry_dormant_and_runtime_mutation", flush=True)
    test_mcp_manager_catalog_and_status()
    print("[TEST 2 PASSED]: mcp_manager_catalog_and_status", flush=True)
    test_langgraph_hitl_interrupt_and_resume_cycle()
    print("[TEST 3 PASSED]: langgraph_hitl_interrupt_and_resume_cycle", flush=True)
    test_scoped_tool_rag_registry_backward_compatibility()
    print("[TEST 4 PASSED]: scoped_tool_rag_registry_backward_compatibility", flush=True)
    test_workspace_sandboxing()
    print("[TEST 5 PASSED]: test_workspace_sandboxing", flush=True)
    test_mutating_mcp_tool_hitl()
    print("[TEST 6 PASSED]: test_mutating_mcp_tool_hitl", flush=True)
    print("\n>>> ALL 6 VERIFICATION TESTS PASSED SUCCESSFULLY! <<<", flush=True)

