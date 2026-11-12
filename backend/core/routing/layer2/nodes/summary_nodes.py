# core/routing/layer2/nodes/summary_nodes.py
from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage, RemoveMessage

from core.routing.layer2.config import DEFAULT_CONFIG
from core.routing.llm_factory import get_chat_companion_llm
from schemas.request_models import AgentState


def summarize_conversation_node(state: AgentState) -> Dict[str, Any]:
    """
    If our conversation gets long, condense older messages into a rolling summary
    and remove them from active short-term memory to keep context windows tiny.
    """
    messages = state.get("messages", [])

    # Only trigger summarization if we have accumulated more than threshold
    if len(messages) <= DEFAULT_CONFIG.max_summary_trigger_length:
        return {}

    existing_summary = state.get("summary", "")

    # Format the conversation history as plain text to prevent model confusion
    history_text = ""
    # Keep the last recent messages (e.g. 4) in active short-term memory
    messages_to_summarize = messages[:-DEFAULT_CONFIG.summary_keep_recent_count]
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
    active_summarizer_llm = get_chat_companion_llm(mode=mode, temperature=DEFAULT_CONFIG.chat_temperature)

    response = active_summarizer_llm.invoke([
        SystemMessage(content="You are a precise conversation summarizer that only outputs the summary."),
        HumanMessage(content=summary_prompt),
    ])

    # Create instructions to delete old messages from the Postgres Checkpointer
    delete_messages_instructions = [RemoveMessage(id=m.id) for m in messages_to_summarize]

    return {
        "summary": response.content.strip(),
        "messages": delete_messages_instructions,
    }

