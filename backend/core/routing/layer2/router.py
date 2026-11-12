# core/routing/layer2/router.py
import os
from typing import Any
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langchain_core.messages import HumanMessage

from schemas.request_models import AgentState
from core.routing.layer2.graph_nodes import (
    tool_retrieval_node,
    route_query,
    summarize_conversation_node,
    memory_retrieval_node,
    document_retrieval_node,
    memory_extraction_node,
    decide_after_tool_retrieval,
    decide_next_step,
    mcp_discovery_node,
    decide_discovery_step,
)
from core.routing.layer2.worker_nodes import execute_tool_node, chat_node

load_dotenv()

# --- BUILD THE GRADIENT COMPILER GRAPH ---
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("memory_retrieval_node", memory_retrieval_node)
builder.add_node("document_retrieval_node", document_retrieval_node)
builder.add_node("tool_retrieval_node", tool_retrieval_node)
builder.add_node("route_query", route_query)
builder.add_node("summarize_conversation_node", summarize_conversation_node)
builder.add_node("execute_tool_node", execute_tool_node)
builder.add_node("chat_node", chat_node)
builder.add_node("memory_extraction_node", memory_extraction_node)
builder.add_node("mcp_discovery_node", mcp_discovery_node)

# Wire the transitions: Memory -> Tool Retrieval -> (bypass LAYA or route_query) -> Action or Document-Grounded Chat
builder.add_edge(START, "memory_retrieval_node")
builder.add_edge("memory_retrieval_node", "tool_retrieval_node")
builder.add_conditional_edges(
    "tool_retrieval_node",
    decide_after_tool_retrieval,
    {
        "document_retrieval_node": "document_retrieval_node",
        "route_query": "route_query",
    },
)

# Route decision: execute_tool_node, mcp_discovery_node, or document_retrieval_node -> chat_node
builder.add_conditional_edges(
    "route_query",
    decide_next_step,
    {
        "document_retrieval_node": "document_retrieval_node",
        "mcp_discovery_node": "mcp_discovery_node",
        "execute_tool_node": "execute_tool_node",
    },
)
builder.add_edge("document_retrieval_node", "chat_node")

# Cyclic MCP addition loop: if approved, loop back to tool_retrieval_node; if rejected, summarize
builder.add_conditional_edges(
    "mcp_discovery_node",
    decide_discovery_step,
    {
        "tool_retrieval_node": "tool_retrieval_node",
        "summarize_conversation_node": "summarize_conversation_node",
    },
)

builder.add_edge("execute_tool_node", "summarize_conversation_node")
builder.add_edge("chat_node", "summarize_conversation_node")

builder.add_edge("summarize_conversation_node", "memory_extraction_node")
builder.add_edge("memory_extraction_node", END)

DB_URI = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/cozmo_db")

# Connection pool settings for serverless DBs (Neon) with fast fallback for dry-run/offline
conn_kwargs = {
    "autocommit": True,
    "row_factory": dict_row,
}

checkpointer = None
use_postgres = False
if os.getenv("DATABASE_URL") and not os.getenv("DISABLE_POSTGRES_CHECKPOINTER"):
    # Avoid blocking offline/dry-run execution on remote cloud DNS lookups
    is_remote = any(x in DB_URI.lower() for x in ["neon.tech", "aws", "azure", "supabase"])
    should_attempt = (not is_remote) or (os.getenv("USE_POSTGRES_CHECKPOINTER", "false").lower() in ("true", "1"))
    if should_attempt:
        try:
            from psycopg import connect
            with connect(DB_URI, connect_timeout=1) as _:
                use_postgres = True
        except Exception:
            use_postgres = False

if use_postgres:
    try:
        pool = ConnectionPool(
            conninfo=DB_URI,
            min_size=1,
            max_size=5,
            kwargs=conn_kwargs,
            check=ConnectionPool.check_connection,
            timeout=2.0,  # Fast timeout so dry-run/offline does not hang
            max_idle=300,
            open=True
        )
        checkpointer = PostgresSaver(pool)
        checkpointer.setup()
        print("[Router DB] PostgresSaver checkpointer initialized successfully.")
    except Exception as db_err:
        print(f"[Router DB Warning]: Postgres checkpointer unavailable ({db_err}). Falling back to MemorySaver.")
        if 'pool' in locals() and pool:
            try:
                pool.close()
            except Exception:
                pass
        checkpointer = MemorySaver()
else:
    checkpointer = MemorySaver()

cozmo_graph = builder.compile(checkpointer=checkpointer)


def run_cozmo_agent(
    user_input: str,
    thread_id: str = "cozmo_default_session",
    provider: str = "local",
    rag_only: bool = False,
    document_namespace: str = "documents",
) -> Any:
    print(f" [run_cozmo_agent] Starting agent run for thread_id='{thread_id}', provider='{provider}'...")
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {
            "session_id": thread_id,
            "application_mode": "Terminal" if thread_id.startswith("terminal") else "Physical_Cozmo"
        }
    }
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "retrieved_memories": [],
        "retrieved_documents": [],
        "rag_only": bool(rag_only),
        "document_namespace": document_namespace or "documents",
        "provider": provider
    }

    print(f" [run_cozmo_agent] Invoking cozmo_graph...")
    result = cozmo_graph.invoke(initial_state, config=config)

    # Check if graph halted on a Human-In-The-Loop interrupt
    state_snapshot = cozmo_graph.get_state(config)
    if state_snapshot.next:
        for task in state_snapshot.tasks:
            if getattr(task, "interrupts", None):
                interrupt_val = task.interrupts[0].value
                print(f" [run_cozmo_agent] HITL Interrupt triggered: {interrupt_val}")
                return {
                    "__interrupt__": True,
                    "payload": interrupt_val
                }

    print(f" [run_cozmo_agent] Finished cozmo_graph successfully!")
    return result["messages"][-1].content


def resume_cozmo_agent(resume_value: Any, thread_id: str = "cozmo_default_session") -> Any:
    print(f" [resume_cozmo_agent] Resuming thread_id='{thread_id}' with value: {resume_value}...")
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {
            "session_id": thread_id,
            "application_mode": "Terminal" if thread_id.startswith("terminal") else "Physical_Cozmo"
        }
    }
    result = cozmo_graph.invoke(Command(resume=resume_value), config=config)

    # Check if another interrupt was triggered
    state_snapshot = cozmo_graph.get_state(config)
    if state_snapshot.next:
        for task in state_snapshot.tasks:
            if getattr(task, "interrupts", None):
                interrupt_val = task.interrupts[0].value
                print(f" [resume_cozmo_agent] Subsequent HITL Interrupt triggered: {interrupt_val}")
                return {
                    "__interrupt__": True,
                    "payload": interrupt_val
                }

    print(f" [resume_cozmo_agent] Finished resume successfully!")
    return result["messages"][-1].content
