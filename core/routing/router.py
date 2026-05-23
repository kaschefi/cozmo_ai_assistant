# core/router.py
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
import os
from tensorflow._api.v2.compat.v1 import config
from schemas.request_models import AgentState, RouteDecision
from actions.digital.n8n_agents import call_n8n_calendar, call_web_search
from actions.digital.langchain_agents import weather_worker
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.routing.tool_vector_db import tool_rag_registry
from psycopg import connect
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import RemoveMessage

GRAY = "\033[90m"
RESET = "\033[0m"

router_llm = ChatOllama(model="qwen2.5:1.5b", temperature=0, base_url="http://localhost:11434")
structured_router = router_llm.with_structured_output(RouteDecision)
chat_llm = ChatOllama(model="qwen2.5:1.5b", temperature=0.6, base_url="http://localhost:11434")


# --- GRAPH NODES ---

def tool_retrieval_node(state: AgentState):
    """
    RAG LAYER STEP 1: Programmatically query our tool database vector space
    to pull only the top 2-3 matching candidates.
    """
    last_message = state["messages"][-1].content
    # Pull top 2 most matching tools to keep the prompt absolutely razor sharp
    matched_tools = tool_rag_registry.search_relevant_tools(last_message, k=2)
    return {"active_tools": matched_tools}


def summarize_conversation_node(state: AgentState):
    """
    If our conversation gets long, condense older messages into a rolling summary
    and remove them from active short-term memory to keep context windows tiny.
    """
    messages = state["messages"]

    # Only trigger summarization if we have accumulated more than 6 messages
    if len(messages) <= 6:
        return {}

    existing_summary = state.get("summary", "")

    # Format the conversation history as plain text to prevent model confusion
    history_text = ""
    # Keep the last 4 messages (2 full exchanges) in active short-term memory
    messages_to_summarize = messages[:-4]
    for m in messages_to_summarize:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        history_text += f"{role}: {m.content}\n"

    summary_prompt = f"""You are a precise conversation summarizer. Your job is to progressively update the summary of a conversation between a User and an Assistant.
    
    Here is the existing summary of the conversation so far:
    "{existing_summary}"
    
    Here are the new lines of conversation that need to be incorporated into the summary:
    {history_text}
    
    Please write a new, concise, updated summary that integrates the new conversation lines into the existing summary. 
    Ensure you preserve key personal details (like the user's name, preferences, or important facts) and key topics discussed.
    Output ONLY the updated summary, with no conversational filler, intros, or outros.
    """

    response = chat_llm.invoke([
        SystemMessage(content="You are a precise conversation summarizer that only outputs the summary."),
        HumanMessage(content=summary_prompt)
    ])

    # Create instructions to delete old messages from the Postgres Checkpointer
    delete_messages_instructions = [RemoveMessage(id=m.id) for m in messages_to_summarize]

    return {
        "summary": response.content.strip(),
        "messages": delete_messages_instructions
    }


def route_query(state: AgentState):
    last_message = state["messages"][-1].content
    active_tools = state.get("active_tools", [])

    # Format the retrieved tools dynamically
    tool_menu_string = ""
    for tool in active_tools:
        tool_menu_string += f'- "{tool["name"]}": {tool["description"]}\n'

    dynamic_prompt = f"""You are Cozmo's routing supervisor. Your role is to accurately classify the intent of the user's latest message.
        AVAILABLE UTILITY CHANNELS RETRIEVED FOR THIS TURN:
        {tool_menu_string}- "none": Core conversational channel. Fall back to this for anything that doesn't strictly match a specific tool option above.
        
        CLASSIFICATION PHILOSOPHY & CRITERIA:
        1. INTENT-DRIVEN SELECTION: You must ONLY select a specific tool node if the user is explicitly requesting an action, operation, or real-time data lookup that requires external service execution. 
        2. CASUAL CHAT & PERSONAL FACTS ("none"): If the user is sharing personal information, making states of being, telling you facts about themselves, greeting you, or engaging in casual/philosophical discussion, you MUST select "none".
        3. TOOL BOUNDARY RULE: Never assume or extrapolate. If a query vaguely mentions a topic but does not contain a clear directive to execute a tool's capability, keep the execution local by routing to "none".
        
        STRICT RULES:
        - Output a structured decision containing the exact string name of the chosen route.
        - If no tool matches the intent profile perfectly, output "none".
        - Never attempt to answer or fulfill the user's request yourself. Your only job is classification.
        """

    decision = structured_router.invoke([
        SystemMessage(content=dynamic_prompt),
        HumanMessage(content=last_message)
    ])

    print(f"\n{GRAY} LangGraph Dynamic Decision: {decision.route}{RESET}")
    return {"next_route": decision.route}

# --- WORKER NODES  ---

def calendar_node(state: AgentState):
    last_message = state["messages"][-1].content
    n8n_reply = call_n8n_calendar(last_message)
    return {"messages": [AIMessage(content=n8n_reply)]}


def web_search_node(state: AgentState):
    last_message = state["messages"][-1].content
    reply = call_web_search(last_message)
    if not reply:
        reply = "I tried searching, but couldn't reach the search service."
    return {"messages": [AIMessage(content=reply)]}


def weather_node(state: AgentState):
    result = weather_worker.invoke({"messages": state["messages"]})
    return {"messages": [result["messages"][-1]]}


def chat_node(state: AgentState):
    print(f"{GRAY}Routing to local chat...{RESET}")
    existing_summary = state.get("summary", "")
    messages_payload = []

    if existing_summary:
        messages_payload.append(
            SystemMessage(
                content=f"You are Cozmo. Here is a summary of the conversation history so far for context: {existing_summary}")
        )
    messages_payload.extend(state["messages"])
    response = chat_llm.invoke(messages_payload)
    return {"messages": [response]}

def decide_next_step(state: AgentState) -> str:
    """Evaluates router output and targets a node execution branch."""
    route = state.get("next_route", "none")
    # If the LLM returned an active valid tool node, go there. Otherwise fallback to chat.
    if route in ["calendar_node", "web_search_node", "weather_node"]:
        return route
    return "chat_node"


# --- BUILD THE GRADIENT COMPILER GRAPH ---
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("tool_retrieval_node", tool_retrieval_node)
builder.add_node("route_query", route_query)
builder.add_node("summarize_conversation_node", summarize_conversation_node)
builder.add_node("calendar_node", calendar_node)
builder.add_node("web_search_node", web_search_node)
builder.add_node("weather_node", weather_node)
builder.add_node("chat_node", chat_node)

# Wire the transitions
builder.add_edge(START, "tool_retrieval_node")
builder.add_edge("tool_retrieval_node", "route_query")
builder.add_conditional_edges("route_query", decide_next_step)

builder.add_edge("calendar_node", "summarize_conversation_node")
builder.add_edge("web_search_node", "summarize_conversation_node")
builder.add_edge("weather_node", "summarize_conversation_node")
builder.add_edge("chat_node", "summarize_conversation_node")

builder.add_edge("summarize_conversation_node", END)


DB_URI = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/cozmo_db")

# Crucial for LangGraph compatibility & table schema auto-migrations
conn_kwargs = {
    "autocommit": True,
    "row_factory": dict_row
}
try:
    conn = connect(DB_URI, **conn_kwargs)
    checkpointer = PostgresSaver(conn)
    checkpointer.setup()

    cozmo_graph = builder.compile(checkpointer=checkpointer)
    print(" Postgres checkpointer initialized successfully.")
except Exception as db_err:
    print(f" Checkpointer connection failed: {db_err}. Falling back to uncompiled builder.")
    cozmo_graph = builder.compile()  # Fallback to stateless memory if DB is down


def run_cozmo_agent(user_input: str,thread_id: str = "cozmo_default_session") -> str:
    initial_state = {"messages": [HumanMessage(content=user_input)]}
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "retrieved_memories": []  # Empty initial layer container
    }

    result = cozmo_graph.invoke(initial_state, config=config)
    return result["messages"][-1].content