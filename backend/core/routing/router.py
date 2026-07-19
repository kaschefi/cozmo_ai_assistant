# core/router.py
from actions.digital.code_executor import code_executor
from core.routing.llm_factory import get_llm
from langgraph.graph import StateGraph, START, END
import os
from dotenv import load_dotenv
from schemas.memory_db import long_term_memory
from schemas.request_models import AgentState, RouteDecision
from actions.digital.n8n_agents import call_n8n_calendar, call_web_search
from actions.digital.langchain_agents import weather_worker
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.routing.tool_vector_db import tool_rag_registry
from psycopg import connect
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import RemoveMessage
from langsmith import traceable
from actions.digital.calendar_agent import run_calendar_agent
load_dotenv()


GRAY = "\033[90m"
RESET = "\033[0m"

router_llm = get_llm("ROUTER_LLM_MODEL", "qwen2.5:3b", temperature=0)
structured_router = router_llm.with_structured_output(RouteDecision)
chat_llm = get_llm("CHAT_LLM_MODEL", "gemma4:e2b", temperature=0.6)


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

    import threading
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
                    import re
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
                        #print(f"\n{GRAY} [LONG-TERM MEMORY UPDATE]: Saved -> {clean_fact} ({category}){RESET}\n: ", end="")
                        import sys
                        sys.stdout.flush()
        except Exception as e:
            print(f"\n{GRAY} [LONG-TERM MEMORY ERROR]: Failed background extraction: {e}{RESET}\n: ", end="")
            import sys
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

# --- WORKER NODES  ---

def calendar_node(state: AgentState):
    last_message = state["messages"][-1].content
    reply = run_calendar_agent(last_message)
    return {"messages": [AIMessage(content=reply)]}


def web_search_node(state: AgentState):
    last_message = state["messages"][-1].content
    reply = call_web_search(last_message)
    if not reply:
        reply = "I tried searching, but couldn't reach the search service."
    return {"messages": [AIMessage(content=reply)]}


def weather_node(state: AgentState):
    """
    Direct single-turn Weather Node:
    1. Extract the city from the user query using a precise prompt (default to Vienna).
    2. Call the get_weather Python function directly.
    3. Feed the raw weather text to the LLM to format a friendly conversational response.
    """
    last_message = state["messages"][-1].content
    
    # Step 1: Extract city using a fast LLM call
    city_prompt = f"""You are a precise city name extractor. Extract the city name mentioned in this query.
    If no city is explicitly mentioned, output ONLY 'Vienna'.
    Output ONLY the city name, with no other words, punctuation, or formatting.
    
    Query: "{last_message}"
    """
    city_response = chat_llm.invoke([
        SystemMessage(content="You extract city names. Output ONLY the city name, nothing else."),
        HumanMessage(content=city_prompt)
    ])
    city = city_response.content.strip().strip("'\"").strip()
    if not city or len(city.split()) > 3: # Fallback if model outputs a sentence
        city = "Vienna"
        
    # Step 2: Call the Python get_weather function directly
    from actions.digital.langchain_agents import get_weather
    raw_weather = get_weather.func(city)

    # Parsing weather details for face display
    import re
    # Extract temperature (digits, optionally signed)
    temp_match = re.search(r'([+-]?\d+)', raw_weather)
    temp = temp_match.group(1) if temp_match else "15"
    
    # Map condition
    raw_lower = raw_weather.lower()
    if any(x in raw_lower for x in ["rain", "drizzle", "shower"]):
        cond = "rainy"
    elif any(x in raw_lower for x in ["snow", "ice", "flurry"]):
        cond = "snowy"
    elif any(x in raw_lower for x in ["cloud", "overcast", "mist", "fog"]):
        cond = "cloudy"
    elif any(x in raw_lower for x in ["thunder", "storm", "lightning"]):
        cond = "stormy"
    else:
        cond = "sunny"

    # Trigger Cozmo Face weather update in Robot Mode directly via Python (prevents loopback deadlocks)
    from core.hardware.connection import cozmo_manager
    if cozmo_manager.robot_mode:
        try:
            cli = cozmo_manager.get_robot()
            if cli:
                import asyncio
                
                # Run a background loop to periodically redraw the weather face
                # This prevents pycozmo speech/movement animations from overwriting the screen buffer!
                async def draw_weather_loop():
                    from actions.physical.face import FaceLibrary
                    face = FaceLibrary(cli)
                    
                    # Redraw every 1.5 seconds for 30 seconds (20 iterations) to keep display stable without Wi-Fi/Audio packet congestion
                    for _ in range(20):
                        try:
                            face.act_weather(temp, cond)
                        except Exception:
                            pass
                        await asyncio.sleep(1.5)
                    
                    # Return to standard eyes after 30 seconds
                    try:
                        face.act_reset()
                    except Exception:
                        pass
                
                asyncio.create_task(draw_weather_loop())
        except Exception as e:
            print(f"Error drawing weather on face: {e}")
    
    # Step 3: Generate the conversational response including the temperature degrees
    weather_prompt = f"""You are Cozmo, a friendly robot assistant. 
    Here is the raw weather data fetched for the city of '{city}':
    "{raw_weather}"
    
    Based on this raw data, write a short, natural, conversational response that you can speak out loud.
    You MUST explicitly include the exact temperature in degrees (in Celsius). Never output just the condition (like 'sunny') without the exact temperature degrees.
    Keep it to a single friendly sentence.
    """
    
    response = chat_llm.invoke([
        SystemMessage(content="You are Cozmo. Write a friendly, single-sentence weather update including the exact temperature degrees."),
        HumanMessage(content=weather_prompt)
    ])
    
    return {"messages": [AIMessage(content=response.content.strip())]}


def chat_node(state: AgentState):
    existing_summary = state.get("summary", "")
    retrieved_memories = state.get("retrieved_memories", [])
    messages_payload = []

    system_instructions = (
        "You are Cozmo, an advanced personal robot assistant with a persistent long-term memory core. "
        "Be friendly, highly conversational, and helpful.\n"
        "CONVERSATIONAL HYGIENE RULES:\n"
        "1. Never 'flex' or list all of your memory core facts unsolicited in a single response.\n"
        "2. Keep your responses short, natural, and highly focused on the user's latest statement (1-2 sentences max).\n"
        "3. Only mention a fact if it is directly and naturally relevant to the user's latest message. Treat your memories as silent background knowledge."
    )
    if existing_summary:
        system_instructions += f"Summary of the current chat session: {existing_summary} "
        
    if retrieved_memories:
        facts_str = "\n".join(f"- {fact}" for fact in retrieved_memories)
        system_instructions += (
            f"\n\n[LONG-TERM MEMORY CORE]\n"
            f"You permanently remember the following historical facts about this user:\n"
            f"{facts_str}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Treat these facts as absolute, undeniable truths from past interactions.\n"
            f"2. Never break character, and never explain technical AI limitations or state that you cannot remember things across sessions."
        )

    messages_payload.append(SystemMessage(content=system_instructions))
    messages_payload.extend(state["messages"])

    response = chat_llm.invoke(messages_payload)
    return {"messages": [response]}

def code_executor_node(state: AgentState):
    last_message = state["messages"][-1].content
    reply = code_executor(last_message)
    return {"messages": [AIMessage(content=reply)]}



TOOL_REGISTRY = {
    "calendar_node": calendar_node,
    "web_search_node": web_search_node,
    "weather_node": weather_node,
    "code_executor_node": code_executor_node,
}

def execute_tool_node(state: AgentState):
    route = state.get("next_route", "none")
    handler = TOOL_REGISTRY.get(route)
    if handler:
        return handler(state)
    return {"messages": [AIMessage(content=f"Error: Tool handler for '{route}' not found.")]}

def decide_next_step(state: AgentState) -> str:
    """Evaluates router output and targets a node execution branch."""
    route = state.get("next_route", "none")
    if route in TOOL_REGISTRY:
        return "execute_tool_node"
    return "chat_node"


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
except Exception as db_err:
    cozmo_graph = builder.compile()  # Fallback to stateless memory if DB is down


def run_cozmo_agent(user_input: str,thread_id: str = "cozmo_default_session") -> str:
    initial_state = {"messages": [HumanMessage(content=user_input)]}
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {
            "session_id": thread_id,
            "application_mode": "Terminal" if thread_id.startswith("terminal") else "Physical_Cozmo"
        }
    }
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "retrieved_memories": []  # Empty initial layer container
    }

    result = cozmo_graph.invoke(initial_state, config=config)
    return result["messages"][-1].content