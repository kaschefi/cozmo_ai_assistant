# core/routing/layer2/worker_nodes.py
import re
import asyncio
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from core.routing.llm_factory import get_llm
from schemas.request_models import AgentState

chat_llm = get_llm("CHAT_LLM_MODEL", "gemma4:e2b", temperature=0.6)


def calendar_node(state: AgentState):
    from actions.digital.langgraph.calendar_agent import run_calendar_agent
    last_message = state["messages"][-1].content
    reply = run_calendar_agent(last_message)
    return {"messages": [AIMessage(content=reply)]}


def web_search_node(state: AgentState):
    from actions.digital.n8n_agents import call_web_search
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
    
    # Step 1: Fast regex city extraction (defaults to Vienna in <1ms)
    city = "Vienna"
    city_match = re.search(r'\bin\s+([A-Za-z\s]+)', last_message, re.IGNORECASE)
    if city_match:
        extracted = city_match.group(1).strip()
        if len(extracted.split()) <= 2:
            city = extracted
        
    # Step 2: Call the Python get_weather function directly
    from actions.digital.langchain.weather_agent import get_weather
    raw_weather = get_weather.func(city)

    # Parsing weather details for face display
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
    from actions.digital.langchain.code_executor import code_executor
    last_message = state["messages"][-1].content
    reply = code_executor(last_message)
    return {"messages": [AIMessage(content=reply)]}


def todolist_node(state: AgentState):
    from actions.digital.langgraph.todolist_agent import run_todolist_agent
    last_message = state["messages"][-1].content
    reply = run_todolist_agent(last_message)
    return {"messages": [AIMessage(content=reply)]}


def move_forward_node(state: AgentState):
    import asyncio
    from actions.physical.movement import move_forward
    try:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(move_forward(distance_mm=100.0))
    except Exception:
        res = "Moving forward."
    return {"messages": [AIMessage(content=str(res))]}


def move_backward_node(state: AgentState):
    import asyncio
    from actions.physical.movement import move_backward
    try:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(move_backward(distance_mm=100.0))
    except Exception:
        res = "Moving backward."
    return {"messages": [AIMessage(content=str(res))]}


def turn_left_node(state: AgentState):
    import asyncio
    from actions.physical.movement import turn_left
    try:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(turn_left(angle_degrees=90.0))
    except Exception:
        res = "Turning left."
    return {"messages": [AIMessage(content=str(res))]}


def turn_right_node(state: AgentState):
    import asyncio
    from actions.physical.movement import turn_right
    try:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(turn_right(angle_degrees=90.0))
    except Exception:
        res = "Turning right."
    return {"messages": [AIMessage(content=str(res))]}


def turn_around_node(state: AgentState):
    import asyncio
    from actions.physical.movement import turn_around
    try:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(turn_around())
    except Exception:
        res = "Turning around."
    return {"messages": [AIMessage(content=str(res))]}


def stop_movement_node(state: AgentState):
    import asyncio
    from actions.physical.movement import stop_movement
    try:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(stop_movement())
    except Exception:
        res = "Stopping all movement."
    return {"messages": [AIMessage(content=str(res))]}


def dock_with_charger_node(state: AgentState):
    import asyncio
    from actions.physical.charger import dock_with_charger
    try:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(dock_with_charger())
    except Exception:
        res = "Docking with charger."
    return {"messages": [AIMessage(content=str(res))]}


def arc_sweep_node(state: AgentState):
    import asyncio
    from actions.physical.movement import arc_sweep
    try:
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(arc_sweep())
    except Exception:
        res = "Scanning surroundings."
    return {"messages": [AIMessage(content=str(res))]}


def setup_gaming_node(state: AgentState):
    import asyncio
    from actions.digital.setups import setup_gaming
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(setup_gaming())
        res = "Gaming setup launched."
    except Exception as e:
        res = f"Gaming setup error: {e}"
    return {"messages": [AIMessage(content=res)]}


def setup_study_node(state: AgentState):
    import asyncio
    from actions.digital.setups import setup_study
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(setup_study())
        res = "Study setup launched."
    except Exception as e:
        res = f"Study setup error: {e}"
    return {"messages": [AIMessage(content=res)]}


def setup_coding_node(state: AgentState):
    import asyncio
    from actions.digital.setups import setup_coding
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(setup_coding())
        res = "Coding setup launched."
    except Exception as e:
        res = f"Coding setup error: {e}"
    return {"messages": [AIMessage(content=res)]}


def tell_time_node(state: AgentState):
    from datetime import datetime
    current_time = datetime.now().strftime("%I:%M %p")
    return {"messages": [AIMessage(content=f"The time is exactly {current_time}.")]}


def get_date_node(state: AgentState):
    from datetime import datetime
    today = datetime.now().strftime("%A, %B %d, %Y")
    return {"messages": [AIMessage(content=f"Today is {today}.")]}


TOOL_REGISTRY = {
    # Cognitive agent tools
    "calendar_node": calendar_node,
    "web_search_node": web_search_node,
    "weather_node": weather_node,
    "code_executor_node": code_executor_node,
    "todolist_node": todolist_node,
    # Physical movement fallbacks
    "move_forward": move_forward_node,
    "move_backward": move_backward_node,
    "turn_left": turn_left_node,
    "turn_right": turn_right_node,
    "turn_around": turn_around_node,
    "stop_movement": stop_movement_node,
    "dock_with_charger": dock_with_charger_node,
    "arc_sweep": arc_sweep_node,
    # Digital setups and system fallbacks
    "setup_gaming": setup_gaming_node,
    "setup_study": setup_study_node,
    "setup_coding": setup_coding_node,
    "tell_time": tell_time_node,
    "get_date": get_date_node,
}


def execute_tool_node(state: AgentState):
    route = state.get("next_route", "none")
    handler = TOOL_REGISTRY.get(route)
    if handler:
        return handler(state)
    return {"messages": [AIMessage(content=f"Error: Tool handler for '{route}' not found.")]}
