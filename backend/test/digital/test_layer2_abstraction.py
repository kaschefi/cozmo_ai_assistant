# backend/test/digital/test_layer2_abstraction.py
"""
Comprehensive Regression & Unit Test Suite for the Layer 2 Cognitive Routing Abstraction.
Validates:
1. Heuristics & Intent Classifiers (heuristics.py)
2. Routing Engine & Decision Logic (engine/laya_engine.py)
3. Node Handlers (nodes/memory, retrieval, routing, summary, mcp)
4. Backward Compatibility Facade (graph_nodes.py)
5. Full LangGraph Construction (router.py)
Runs 100% hardware-free (--dry-run).
"""
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure test runs offline/dry-run without postgres delays
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["DISABLE_POSTGRES_CHECKPOINTER"] = "1"
os.environ["USE_TF"] = "0"

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from core.routing.layer2.config import Layer2Config, DEFAULT_CONFIG
from core.routing.layer2.heuristics import (
    is_file_operation_query,
    is_workstation_setup_query,
    filter_setup_tools,
    build_contextual_rag_query,
)
from core.routing.layer2.engine.base import BaseRoutingEngine, RouteDecisionResult
from core.routing.layer2.engine.laya_engine import LayaRoutingEngine, get_laya_agent
from core.routing.layer2.nodes.memory_nodes import (
    memory_retrieval_node,
    memory_extraction_node,
)
from core.routing.layer2.nodes.retrieval_nodes import (
    document_retrieval_node,
    tool_retrieval_node,
)
from core.routing.layer2.nodes.routing_nodes import (
    route_query,
    decide_after_tool_retrieval,
    decide_next_step,
    decide_discovery_step,
    get_routing_engine,
    set_routing_engine,
)
from core.routing.layer2.nodes.summary_nodes import summarize_conversation_node
from core.routing.layer2.nodes.mcp_nodes import mcp_discovery_node
import core.routing.layer2.graph_nodes as graph_nodes_facade


def test_heuristics_file_operations():
    """Validates regex detection of file & directory manipulation queries."""
    # File extensions with actions
    assert is_file_operation_query("can you make a new file called test.md") is True
    assert is_file_operation_query("please create script.py in workspace") is True
    assert is_file_operation_query("write notes.txt for me") is True
    assert is_file_operation_query("inspect config.json") is True

    # Mutating verbs with nouns
    assert is_file_operation_query("create a new directory called assets") is True
    assert is_file_operation_query("delete the old folder") is True

    # Read-only document queries (excluding uploaded RAG docs)
    assert is_file_operation_query("read document") is True
    assert is_file_operation_query("read uploaded document") is False
    assert is_file_operation_query("what does the thesis say") is False

    # Non-file queries
    assert is_file_operation_query("launch pycharm for coding") is False
    assert is_file_operation_query("what is the weather in Paris?") is False
    assert is_file_operation_query("") is False


def test_heuristics_workstation_setups():
    """Validates detection of explicit setup launcher commands vs questions/file ops."""
    # Explicit setups
    assert is_workstation_setup_query("set up coding mode") is True
    assert is_workstation_setup_query("prepare my gaming setup") is True
    assert is_workstation_setup_query("open steam and launch discord") is True
    assert is_workstation_setup_query("time to study") is True
    assert is_workstation_setup_query("setup coding") is True

    # Exclusions: questions or doc references
    assert is_workstation_setup_query("what is study mode?") is False
    assert is_workstation_setup_query("can you explain the specification document?") is False
    assert is_workstation_setup_query("make a file called code.py") is False  # File op overrides setup
    assert is_workstation_setup_query("") is False


def test_heuristics_filter_setup_tools():
    """Validates setup launcher tools are excluded on non-setup queries."""
    tools = [
        {"name": "weather_node"},
        {"name": "setup_coding"},
        {"name": "setup_gaming"},
    ]
    # Non-setup query: setups removed
    filtered = filter_setup_tools(tools, "what is the temperature today?")
    assert [t["name"] for t in filtered] == ["weather_node"]

    # Explicit setup query: setups retained
    retained = filter_setup_tools(tools, "start gaming session")
    assert len(retained) == 3


def test_heuristics_contextual_rag_query():
    """Validates multi-turn context synthesis for short follow-up questions."""
    # Short follow-up gets combined
    messages = [
        HumanMessage(content="What are the system requirements for MoKa?"),
        AIMessage(content="MoKa requires 8GB RAM and Python 3.10."),
        HumanMessage(content="Tell me more about that"),
    ]
    query = build_contextual_rag_query(messages)
    assert "What are the system requirements for MoKa?" in query
    assert "Follow-up: Tell me more about that" in query

    # Long query stays untouched
    long_msg = [HumanMessage(content="Explain in detail how the fast reflexive layer works across all nodes")]
    assert build_contextual_rag_query(long_msg) == "Explain in detail how the fast reflexive layer works across all nodes"
    assert build_contextual_rag_query([]) == ""


def test_engine_routing_decisions_and_guards():
    """Validates LayaRoutingEngine inference, guardrails, and gating."""
    engine = LayaRoutingEngine()

    active_tools = [
        {"name": "setup_coding", "description": "IDE launcher", "source_type": "native"},
        {"name": "mcp_pack_filesystem", "description": "Filesystem operations", "source_type": "mcp_dormant", "server_pack_id": "mcp_pack_filesystem"},
    ]

    # Guard 1: File operation must override setup_coding to filesystem tool
    with patch("core.routing.layer2.graph_nodes.get_laya_agent") as mock_laya:
        mock_laya.return_value.predict.return_value = {
            "answers": {"tool_selection": {"choice": "setup_coding", "confidence": 0.8}}
        }
        res = engine.select_route("can you create a new file named test.md", active_tools)
        assert res.route == "mcp_pack_filesystem"

    # Guard 2: Workstation setup chosen on a non-setup query falls back to 'none'
    non_setup_tools = [
        {"name": "setup_gaming", "description": "Gaming mode launcher", "source_type": "native"},
    ]
    with patch("core.routing.layer2.graph_nodes.get_laya_agent") as mock_laya:
        mock_laya.return_value.predict.return_value = {
            "answers": {"tool_selection": {"choice": "setup_gaming", "confidence": 0.9}}
        }
        res = engine.select_route("what is your favorite game?", non_setup_tools)
        assert res.route == "none"

    # Anti-hallucination gating: flat noise confidence (< 0.05) and weak match (> 0.82) -> none
    weak_tools = [
        {"name": "tavily_search", "description": "Web search", "score": 0.95}
    ]
    with patch("core.routing.layer2.graph_nodes.get_laya_agent") as mock_laya:
        mock_laya.return_value.predict.return_value = {
            "answers": {"tool_selection": {"choice": "tavily_search", "confidence": 0.02}}
        }
        res = engine.select_route("hello there", weak_tools)
        assert res.route == "none"

    # None override: FAISS has a strong match (score <= 0.65) and none confidence is weak (< 0.12)
    strong_tools = [
        {"name": "weather_node", "description": "Check weather", "score": 0.50}
    ]
    with patch("core.routing.layer2.graph_nodes.get_laya_agent") as mock_laya:
        mock_laya.return_value.predict.return_value = {
            "answers": {
                "tool_selection": {
                    "choice": "none",
                    "confidence": 0.08,
                    "probabilities": {"weather_node": 0.40, "none": 0.08}
                }
            }
        }
        res = engine.select_route("is it raining outside?", strong_tools)
        assert res.route == "weather_node"


def test_nodes_memory():
    """Validates memory retrieval & extraction nodes."""
    # 1. Meta-trigger query
    meta_state = {
        "messages": [HumanMessage(content="what facts do you know about me?")]
    }
    with patch("sync_memory.check_and_sync_memory_if_modified", return_value=False), \
         patch("core.routing.layer2.graph_nodes.long_term_memory") as mock_mem:
        mock_mem.get_all_memories.return_value = [{"fact": "User is named Cozmo Owner"}]
        res = memory_retrieval_node(meta_state)
        assert "retrieved_memories" in res
        assert len(res["retrieved_memories"]) == 1

    # 2. Memory extraction async execution
    extract_state = {
        "messages": [
            HumanMessage(content="I am a software engineer"),
            AIMessage(content="Nice to meet you!"),
            HumanMessage(content="I love building robots"),
        ]
    }
    with patch("core.routing.layer2.graph_nodes.threading.Thread") as mock_thread:
        res = memory_extraction_node(extract_state)
        assert res == {}
        assert mock_thread.called


def test_nodes_routing_and_edges():
    """Validates conditional edges and routing dispatch."""
    # decide_after_tool_retrieval:
    # rag_only or document query -> document_retrieval_node
    assert decide_after_tool_retrieval({"rag_only": True}) == "document_retrieval_node"
    doc_state = {
        "active_tools": [],
        "messages": [HumanMessage(content="what are the conclusions in the srs document?")]
    }
    assert decide_after_tool_retrieval(doc_state) == "document_retrieval_node"

    # Ordinary chat with no tools -> chat_node (skips document search)
    chat_state = {
        "active_tools": [],
        "messages": [HumanMessage(content="hello, how are you?")]
    }
    assert decide_after_tool_retrieval(chat_state) == "chat_node"
    assert decide_after_tool_retrieval({"active_tools": [{"name": "tool1"}]}) == "route_query"

    # decide_next_step:
    # Casual chat routes directly to chat_node
    assert decide_next_step({"next_route": "none", "messages": [HumanMessage(content="hi there")]}) == "chat_node"
    # Document inquiry routes to document_retrieval_node
    assert decide_next_step({"next_route": "none", "messages": [HumanMessage(content="what does the pdf say?")]}) == "document_retrieval_node"
    assert decide_next_step({
        "next_route": "mcp_pack_github",
        "active_tools": [{"name": "mcp_pack_github", "source_type": "mcp_dormant"}]
    }) == "mcp_discovery_node"
    assert decide_next_step({"next_route": "weather_node", "active_tools": []}) == "execute_tool_node"

    # decide_discovery_step
    assert decide_discovery_step({"next_route": "re_evaluate"}) == "tool_retrieval_node"
    assert decide_discovery_step({"next_route": "none"}) == "summarize_conversation_node"


def test_nodes_summary():
    """Validates summarization trigger threshold and message trimming."""
    # Under threshold: no summary
    short_state = {"messages": [HumanMessage(content="hi"), AIMessage(content="hello")]}
    assert summarize_conversation_node(short_state) == {}

    # Over threshold: summarizes older messages
    long_msgs = [HumanMessage(content=f"msg {i}") for i in range(8)]
    long_state = {"messages": long_msgs, "provider": "local"}
    with patch("core.routing.layer2.nodes.summary_nodes.get_chat_companion_llm") as mock_llm_factory:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Summary of earlier messages.")
        mock_llm_factory.return_value = mock_llm

        res = summarize_conversation_node(long_state)
        assert res["summary"] == "Summary of earlier messages."
        assert len(res["messages"]) == 4  # Removed 4 oldest


def test_graph_nodes_facade_backward_compatibility():
    """Validates that graph_nodes facade maintains all original symbols and signatures."""
    expected_symbols = [
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
    for sym in expected_symbols:
        assert hasattr(graph_nodes_facade, sym), f"Missing symbol '{sym}' in graph_nodes facade!"

    # Verify route_query invoked via facade behaves identically
    state = {
        "messages": [HumanMessage(content="hello there")],
        "active_tools": [],
    }
    assert graph_nodes_facade.route_query(state) == {"next_route": "none"}


def test_langgraph_router_compilation():
    """Verifies that router.py compiles cozmo_graph cleanly with the abstracted nodes."""
    from core.routing.layer2.router import cozmo_graph, builder

    assert cozmo_graph is not None
    # Check that core nodes are registered in the builder
    expected_nodes = {
        "memory_retrieval_node",
        "document_retrieval_node",
        "tool_retrieval_node",
        "route_query",
        "summarize_conversation_node",
        "execute_tool_node",
        "chat_node",
        "memory_extraction_node",
        "mcp_discovery_node",
    }
    registered_nodes = set(builder.nodes.keys())
    assert expected_nodes.issubset(registered_nodes), f"Missing nodes: {expected_nodes - registered_nodes}"


if __name__ == "__main__":
    print("Running Layer 2 Abstraction Verification Suite...", flush=True)
    test_heuristics_file_operations()
    print("[TEST 1 PASSED]: heuristics_file_operations", flush=True)
    test_heuristics_workstation_setups()
    print("[TEST 2 PASSED]: heuristics_workstation_setups", flush=True)
    test_heuristics_filter_setup_tools()
    print("[TEST 3 PASSED]: heuristics_filter_setup_tools", flush=True)
    test_heuristics_contextual_rag_query()
    print("[TEST 4 PASSED]: heuristics_contextual_rag_query", flush=True)
    test_engine_routing_decisions_and_guards()
    print("[TEST 5 PASSED]: engine_routing_decisions_and_guards", flush=True)
    test_nodes_memory()
    print("[TEST 6 PASSED]: nodes_memory", flush=True)
    test_nodes_routing_and_edges()
    print("[TEST 7 PASSED]: nodes_routing_and_edges", flush=True)
    test_nodes_summary()
    print("[TEST 8 PASSED]: nodes_summary", flush=True)
    test_graph_nodes_facade_backward_compatibility()
    print("[TEST 9 PASSED]: graph_nodes_facade_backward_compatibility", flush=True)
    test_langgraph_router_compilation()
    print("[TEST 10 PASSED]: langgraph_router_compilation", flush=True)
    print("\n>>> ALL 10 LAYER 2 ABSTRACTION TESTS PASSED! <<<", flush=True)
