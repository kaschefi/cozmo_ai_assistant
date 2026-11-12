# core/routing/layer2/nodes/memory_nodes.py
import sys
import threading
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langsmith import traceable

from core.routing.layer2.config import DEFAULT_CONFIG
from schemas.request_models import AgentState

GRAY = "\033[90m"
RESET = "\033[0m"


def _get_active_memory():
    gn = sys.modules.get("core.routing.layer2.graph_nodes")
    if gn and hasattr(gn, "long_term_memory"):
        return gn.long_term_memory
    from schemas.memory_db import long_term_memory
    return long_term_memory


def _get_active_thread_class():
    gn = sys.modules.get("core.routing.layer2.graph_nodes")
    if gn and hasattr(gn, "threading") and hasattr(gn.threading, "Thread"):
        return gn.threading.Thread
    return threading.Thread


def memory_retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    Step 1: Runs a quick similarity check against the permanent database
    using the user's latest input string and the owner ID.
    Directly pulls all facts on broad meta-queries requesting profile summaries.
    """
    user_id = DEFAULT_CONFIG.default_user_id

    # Synchronize any manual edits in user_profile.md before memory lookup
    try:
        from sync_memory import check_and_sync_memory_if_modified
        check_and_sync_memory_if_modified(user_id=user_id)
    except Exception:
        pass

    last_message = state["messages"][-1].content
    memory_db = _get_active_memory()

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
        "facts you know",
    ]
    if any(trigger in q for trigger in meta_triggers):
        # Pull all saved facts directly (up to recent 15) to bypass vector limitations on meta-queries
        memories = memory_db.get_all_memories(user_id=user_id)
        return {"retrieved_memories": memories[-DEFAULT_CONFIG.meta_memory_limit:]}

    memories = memory_db.retrieve_relevant_memories(
        last_message, user_id=user_id, limit=DEFAULT_CONFIG.memory_retrieve_limit
    )
    return {"retrieved_memories": memories}


def memory_extraction_node(state: AgentState) -> Dict[str, Any]:
    """
    Step 2: Scans the recent conversation history for permanent profile traits.
    Runs Mem0 asynchronously in a background thread to extract facts, update conflicts,
    and discard ephemeral noise (weather, dates, greetings) without blocking user responses.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    recent_messages = messages[-3:]
    has_doc_context = bool(state.get("retrieved_documents"))
    dialogue_turns = []
    for m in recent_messages:
        is_human = isinstance(m, HumanMessage)
        if has_doc_context and not is_human:
            continue
        role = "user" if is_human else "assistant"
        dialogue_turns.append({"role": role, "content": m.content})

    if not dialogue_turns:
        return {}

    user_id = DEFAULT_CONFIG.default_user_id
    memory_db = _get_active_memory()

    @traceable(name="Mem0 Long-Term Memory Extraction", run_type="chain")
    def run_extraction_bg():
        try:
            memory_db.add_dialogue(dialogue_turns, user_id=user_id)
            sys.stdout.flush()
            try:
                from sync_memory import notify_memory_updated
                notify_memory_updated(user_id=user_id)
            except Exception as se:
                print(f"\n{GRAY} [LONG-TERM MEMORY SYNC NOTICE]: {se}{RESET}\n: ", end="")
                sys.stdout.flush()
        except Exception as e:
            print(f"\n{GRAY} [LONG-TERM MEMORY ERROR]: Failed background extraction: {e}{RESET}\n: ", end="")
            sys.stdout.flush()

    thread_cls = _get_active_thread_class()
    thread_cls(target=run_extraction_bg, daemon=False).start()
    return {}
