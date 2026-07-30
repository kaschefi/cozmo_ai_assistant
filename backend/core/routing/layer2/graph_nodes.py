# core/routing/layer2/graph_nodes.py
import re
import threading
import sys
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, RemoveMessage
from langsmith import traceable

from core.routing.llm_factory import get_llm
from core.routing.layer2.tool_vector_db import tool_rag_registry
from schemas.memory_db import long_term_memory
from schemas.request_models import AgentState, RouteDecision

GRAY = "\033[90m"
RESET = "\033[0m"

router_llm = get_llm("ROUTER_LLM_MODEL", "qwen2.5:3b", temperature=0)
structured_router = router_llm.with_structured_output(RouteDecision)
chat_llm = get_llm("CHAT_LLM_MODEL", "gemma4:e2b", temperature=0.6)


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
        all_rows = long_term_memory._get_all_memories_for_user(user_id)
        memories = [m[1] for m in all_rows[-15:]]
        return {"retrieved_memories": memories}

    memories = long_term_memory.retrieve_relevant_memories(last_message, user_id=user_id, limit=3)
    return {"retrieved_memories": memories}


def memory_extraction_node(state: AgentState):
    """
    Step 2: Scans the recent conversation history for permanent profile traits.
    Strictly discards time, weather, and calendar dates.
    Runs asynchronously in a background thread to avoid blocking user response.
    Non-daemon thread guarantees Postgres writes complete safely even on immediate exit.
    """
    messages = state["messages"]
    if not messages:
        return {}

    # Grab the last 3 messages to preserve dialogue context and spelling corrections
    recent_messages = messages[-3:]
    recent_exchange = ""
    for m in recent_messages:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        recent_exchange += f"{role}: {m.content}\n"
        
    user_id = "cozmo_owner"

    @traceable(name="Long-Term Memory Fact Extraction", run_type="chain")
    def run_extraction_bg():
        try:
            selective_extraction_prompt = f"""You are a profile memory analyzer. Analyze the recent conversation history to see if the user shared permanent personal information.

            STRICT DATA FILTERS:
            - IGNORE all temporary details: current weather conditions, the current time/day, and specific calendar appointment slots (e.g., "meeting at 4pm").
            - EXTRACT only permanent biographical facts:
              1. Identity/Name (e.g., user name, nicknames).
              2. Student status, occupation, profession, field of study, or major (e.g., student, software engineer, studying computer science).
              3. Persistent preferences, interests, or favorites (e.g., favorite sports teams, hobbies, coding languages, software tools, game titles).
              4. Skills, goals, or roles.

            Recent Conversation History:
            {recent_exchange}

            INSTRUCTIONS:
            1. Formulate facts as short, clear, declarative sentences starting with 'The user...'.
            2. For each extracted fact, assign one of these category keys:
               - 'user_name' (if the fact is about their name, nicknames, or identity)
               - 'user_occupation' (if the fact is about being a student, their profession, job, major, or field of study)
               - 'favorite_sports_team' (if it is their favorite sports team)
               - 'favorite_programming_language' (if it is their favorite programming language)
               - 'user_location' (if it's where they live or come from, e.g. Iran)
               - 'general_preference' (for any other hobbies, interests, books, movies, or general facts)
            3. Format each fact line EXACTLY as: Fact | Category_Key
               Example: The user's name is Bob. | user_name
               Example: The user is studying computer science. | user_occupation
            4. If no new permanent personal facts, traits, or preferences are revealed, return exactly 'NONE'.
            5. Output ONLY the raw pipe-separated lines, with no additional conversational text, numbers, or bullet points.
            6. STRICT GUARDRAIL: Only extract facts that the USER explicitly shares, states, or confirms. Never extract facts or preferences from details that the ASSISTANT suggests, hallucinates, or introduces in conversation (e.g., if the Assistant says 'You probably like movies' but the User doesn't explicitly confirm it, DO NOT extract it).
            """

            response = router_llm.invoke([
                SystemMessage(content="You are a precise fact filtering pipeline. Output Fact | Category or 'NONE'."),
                HumanMessage(content=selective_extraction_prompt)
            ])

            cleaned_result = response.content.strip()
            if cleaned_result and cleaned_result != "NONE":
                for fact in cleaned_result.split("\n"):
                    clean_fact = fact.strip()
                    # Robust cleaning: strip list indicators like "1. ", "- ", "* "
                    clean_fact = re.sub(r'^[-*\d.\s]+', '', clean_fact).strip()
                    
                    # Parse pipe separation
                    category = "general_preference"
                    if "|" in clean_fact:
                        parts = clean_fact.split("|", 1)
                        clean_fact = parts[0].strip()
                        category = parts[1].strip()
                    
                    if clean_fact.lower().startswith("the user"):
                        # Standardize prefix casing to "The user"
                        clean_fact = re.sub(r'^[Tt]he\s+[Uu]ser', 'The user', clean_fact)
                        
                        long_term_memory.save_memory(clean_fact, category=category, user_id=user_id)
                        sys.stdout.flush()
        except Exception as e:
            print(f"\n{GRAY} [LONG-TERM MEMORY ERROR]: Failed background extraction: {e}{RESET}\n: ", end="")
            sys.stdout.flush()

    threading.Thread(target=run_extraction_bg, daemon=False).start()
    return {}


def route_query(state: AgentState):
    last_message = state["messages"][-1].content
    active_tools = state.get("active_tools", [])

    # If no tools passed the RAG similarity gate, bypass LLM classification completely
    if not active_tools:
        return {"next_route": "none"}

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

    return {"next_route": decision.route}


def decide_next_step(state: AgentState) -> str:
    """Evaluates router output and targets a node execution branch."""
    from core.routing.layer2.worker_nodes import TOOL_REGISTRY
    route = state.get("next_route", "none")
    if route in TOOL_REGISTRY:
        return "execute_tool_node"
    return "chat_node"
