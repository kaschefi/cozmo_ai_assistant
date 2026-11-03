# core/routing/layer2/router.py
import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage

from schemas.request_models import AgentState
from core.routing.layer2.graph_nodes import (
    tool_retrieval_node,
    route_query,
    summarize_conversation_node,
    memory_retrieval_node,
    memory_extraction_node,
    decide_next_step,
)
from core.routing.layer2.worker_nodes import execute_tool_node, chat_node

load_dotenv()

# --- BUILD THE GRADIENT COMPILER GRAPH ---
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("tool_retrieval_node", tool_retrieval_node)
builder.add_node("route_query", route_query)
builder.add_node("summarize_conversation_node", summarize_conversation_node)
builder.add_node("execute_tool_node", execute_tool_node)
builder.add_node("chat_node", chat_node)
builder.add_node("memory_retrieval_node", memory_retrieval_node)
builder.add_node("memory_extraction_node", memory_extraction_node)

# Wire the transitions
builder.add_edge(START, "memory_retrieval_node")
builder.add_edge("memory_retrieval_node", "tool_retrieval_node")
builder.add_edge("tool_retrieval_node", "route_query")
builder.add_conditional_edges("route_query", decide_next_step)

builder.add_edge("execute_tool_node", "summarize_conversation_node")
builder.add_edge("chat_node", "summarize_conversation_node")

builder.add_edge("summarize_conversation_node", "memory_extraction_node")
builder.add_edge("memory_extraction_node", END)

DB_URI = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/cozmo_db")

# Crucial for LangGraph compatibility & resilient connection pool for serverless DBs (Neon)
conn_kwargs = {
    "autocommit": True,
    "row_factory": dict_row,
}
try:
    pool = ConnectionPool(
        conninfo=DB_URI,
        min_size=1,
        max_size=10,
        kwargs=conn_kwargs,
        check=ConnectionPool.check_connection,
        max_idle=300,
        open=True
    )
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()

    cozmo_graph = builder.compile(checkpointer=checkpointer)
except Exception as db_err:
    print(f"[Router DB Warning]: Failed to init Postgres checkpointer: {db_err}. Falling back to stateless.")
    cozmo_graph = builder.compile()  # Fallback to stateless memory if DB is down


def run_cozmo_agent(user_input: str, thread_id: str = "cozmo_default_session", provider: str = "local") -> str:
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
        "retrieved_memories": [],  # Empty initial layer container
        "provider": provider
    }

    print(f" [run_cozmo_agent] Invoking cozmo_graph...")
    result = cozmo_graph.invoke(initial_state, config=config)
    print(f" [run_cozmo_agent] Finished cozmo_graph successfully!")
    return result["messages"][-1].content
