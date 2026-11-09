# core/routing/layer2/graph_nodes.py
import re
import threading
import sys
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, RemoveMessage
from langsmith import traceable

import os
os.environ["USE_TF"] = "0"
import laya

from core.routing.llm_factory import get_llm
from core.routing.layer2.tool_vector_db import tool_rag_registry
from schemas.memory_db import long_term_memory
from schemas.request_models import AgentState, RouteDecision

GRAY = "\033[90m"
RESET = "\033[0m"

_LAYA_AGENT = None
_LAYA_LOCK = threading.Lock()

def get_laya_agent(model_id: str = "convaiinnovations/laya-typed-decisions"):
    global _LAYA_AGENT
    if _LAYA_AGENT is None:
        with _LAYA_LOCK:
            if _LAYA_AGENT is None:
                print(f"[LayaRouter] Pre-loading LAYA Typed Decision Model '{model_id}'...")
                _LAYA_AGENT = laya.load(model_id)
                print("[LayaRouter] LAYA Decision Model initialized successfully.")
    return _LAYA_AGENT
chat_llm = get_llm("CHAT_LLM_MODEL", "gemma4:e2b", temperature=0.6)


def is_conversational_query(text: str) -> bool:
    """
    Detects whether user input is purely conversational greeting, acknowledgment, or chit-chat.
    Ensures casual chat prompts bypass tool RAG matching and route straight to chat_node.
    """
    if not text:
        return True
    t = text.strip().lower()
    t_clean = re.sub(r'[^\w\s]', '', t)
    words = t_clean.split()
    if not words:
        return True

    GREETINGS = {
        "hi", "hello", "hey", "hiya", "howdy", "greetings", "yo", "sup",
        "good morning", "good afternoon", "good evening", "good night",
        "how are you", "how are you doing", "hows it going", "how are things",
        "whats up", "what is up", "who are you", "what can you do", "introduce yourself",
        "nice to meet you", "pleased to meet you",
        "thanks", "thank you", "ok", "okay", "cool", "bye", "goodbye"
    }
    if t_clean in GREETINGS:
        return True
    if len(words) <= 2 and words[0] in {"hi", "hello", "hey", "hiya", "yo"}:
        return True
    return False


def tool_retrieval_node(state: AgentState):
    """
    RAG LAYER STEP 1: Programmatically query our tool database vector space
    to pull only the top 5 matching candidates.
    """
    if tool_rag_registry.db is None or not any(d.metadata.get("source_type") == "mcp_dormant" for d in tool_rag_registry._tools_source):
        tool_rag_registry.load_dormant_catalog()
        tool_rag_registry.build_index()

    last_message = state["messages"][-1].content
    if is_conversational_query(last_message):
        return {"active_tools": []}

    # If the user is asking to access external system folders outside MoKa's workspace,
    # bypass tool retrieval so the assistant handles it directly via chat_node without triggering HITL
    from core.routing.layer2.worker_nodes import is_external_system_path_query
    if is_external_system_path_query(last_message):
        return {"active_tools": []}

    # Pull top 5 most matching tools to keep the prompt absolutely razor sharp
    matched_tools = tool_rag_registry.search_relevant_tools(last_message, k=5)
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

    mode = state.get("provider", "local")
    from core.routing.llm_factory import get_chat_companion_llm
    active_summarizer_llm = get_chat_companion_llm(mode=mode, temperature=0.6)

    response = active_summarizer_llm.invoke([
        SystemMessage(content="You are a precise conversation summarizer that only outputs the summary."),
        HumanMessage(content=summary_prompt)
    ])

    # Create instructions to delete old messages from the Postgres Checkpointer
    delete_messages_instructions = [RemoveMessage(id=m.id) for m in messages_to_summarize]

    return {
        "summary": response.content.strip(),
        "messages": delete_messages_instructions
    }


def memory_retrieval_node(state: AgentState):
    """
    Step 1: Runs a quick similarity check against the permanent database
    using the user's latest input string and the owner ID.
    Directly pulls all facts on broad meta-queries requesting profile summaries.
    """
    last_message = state["messages"][-1].content
    user_id = "cozmo_owner"

    # 1. Identify meta-queries requesting profile summary
    q = last_message.lower()
    meta_triggers = [
        "what do you know about me", 
        "what facts do you know", 
        "tell me all the facts", 
        "tell me facts about me", 
        "what do you remember about me", 
        "tell me about myself",
        "my profile",
        "facts you know"
    ]
    if any(trigger in q for trigger in meta_triggers):
        # Pull all saved facts directly (up to recent 15) to bypass vector limitations on meta-queries
        memories = long_term_memory.get_all_memories(user_id=user_id)
        return {"retrieved_memories": memories[-15:]}

    memories = long_term_memory.retrieve_relevant_memories(last_message, user_id=user_id, limit=3)
    return {"retrieved_memories": memories}


def memory_extraction_node(state: AgentState):
    """
    Step 2: Scans the recent conversation history for permanent profile traits.
    Runs Mem0 asynchronously in a background thread to extract facts, update conflicts,
    and discard ephemeral noise (weather, dates, greetings) without blocking user responses.
    """
    messages = state["messages"]
    if not messages:
        return {}

    # Grab the last 3 messages to preserve dialogue context
    recent_messages = messages[-3:]
    dialogue_turns = []
    for m in recent_messages:
        role = "user" if isinstance(m, HumanMessage) else "assistant"
        dialogue_turns.append({"role": role, "content": m.content})

    user_id = "cozmo_owner"

    @traceable(name="Mem0 Long-Term Memory Extraction", run_type="chain")
    def run_extraction_bg():
        try:
            long_term_memory.add_dialogue(dialogue_turns, user_id=user_id)
            sys.stdout.flush()
        except Exception as e:
            print(f"\n{GRAY} [LONG-TERM MEMORY ERROR]: Failed background extraction: {e}{RESET}\n: ", end="")
            sys.stdout.flush()

    threading.Thread(target=run_extraction_bg, daemon=False).start()
    return {}


def route_query(state: AgentState):
    last_message = state["messages"][-1].content
    active_tools = state.get("active_tools", [])

    # Fast-path for conversational greetings or when no tools passed the RAG similarity gate
    if is_conversational_query(last_message) or not active_tools:
        return {"next_route": "none"}

    # Formulate typed choice criteria dictionary from Top-K RAG selection
    tools_dict = {tool["name"]: tool["description"] for tool in active_tools}
    tools_dict["none"] = "Core conversational channel. Select for casual chat, greetings, personal facts, or general discussion."

    questions = {
        "tool_selection": {
            "type": "choice",
            "instructions": (
                "Select the appropriate tool or action to execute given the user's input/state. "
                "If the user input is casual chat, greetings, personal facts, jokes, or does not require "
                "executing any specific action or tool, select 'none'."
            ),
            "criteria": tools_dict,
        }
    }

    try:
        agent = get_laya_agent()
        result = agent.predict(last_message, questions)
        answers = result.get("answers", result)
        decision = answers.get("tool_selection", {})
        selected_route = decision.get("choice", "none")
    except Exception as e:
        print(f"[route_query Error] Laya prediction failed: {e}. Falling back to 'none'.")
        selected_route = "none"

    return {"next_route": selected_route}


def decide_next_step(state: AgentState) -> str:
    """Evaluates router output and targets a node execution branch."""
    route = state.get("next_route", "none")
    if route == "none":
        return "chat_node"

    # Check if route is an uninstalled/dormant MCP pack stub
    active_tools = state.get("active_tools", [])
    tool_meta = next((t for t in active_tools if t.get("name") == route), None)
    if tool_meta and tool_meta.get("source_type") == "mcp_dormant":
        return "mcp_discovery_node"

    # Native tools or dynamically ingested mcp_active tools
    return "execute_tool_node"


def mcp_discovery_node(state: AgentState):
    """
    Gate 1 HITL checkpoint:
    Pauses execution and asks the user whether they want MoKa to add the new tool/MCP pack.
    """
    from langgraph.types import interrupt
    from core.routing.layer2.mcp_manager import mcp_manager

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
        "message": f"I need the '{display_name}' tool to help you with that. Would you like me to add it so I can use it?"
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
                "next_route": "re_evaluate"
            }
        except Exception as e:
            print(f"[mcp_discovery_node Error] Failed to connect '{pack_id}': {e}")
            return {
                "resumed_from_interrupt": True,
                "messages": [AIMessage(content=f"I tried to add '{display_name}', but encountered an issue: {e}")],
                "next_route": "none"
            }
    else:
        print(f"[mcp_discovery_node] User DECLINED adding '{display_name}'.")
        return {
            "resumed_from_interrupt": True,
            "messages": [AIMessage(content=f"Understood! I won't add '{display_name}'. Let me know if you need help with anything else.")],
            "next_route": "none"
        }


def decide_discovery_step(state: AgentState) -> str:
    """Evaluates whether to loop back to tool_retrieval_node after MCP addition or finish."""
    route = state.get("next_route", "none")
    if route == "re_evaluate":
        return "tool_retrieval_node"
    return "summarize_conversation_node"

