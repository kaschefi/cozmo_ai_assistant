# backend/core/routing/baseline/action_handlers.py
"""
Execution dispatchers and wrappers for all actions in the baseline routing system.
Allows the baseline pipeline to execute any chosen action safely.
"""

import asyncio
import inspect
from datetime import datetime
from typing import Dict, Callable, Any

from langchain_core.messages import SystemMessage, HumanMessage
from core.routing.llm_factory import get_llm

chat_llm = get_llm("CHAT_LLM_MODEL", "gemma4:e2b", temperature=0.6)


# -----------------------------------------------------------------------------
# Physical Action Handlers
# -----------------------------------------------------------------------------
async def handle_move_forward(command: str = "", **kwargs) -> str:
    try:
        from actions.physical.movement import move_forward
        res = await move_forward(distance_mm=100.0)
        return str(res)
    except Exception as e:
        return f"Physical move_forward failed or robot not connected: {e}"


async def handle_move_backward(command: str = "", **kwargs) -> str:
    try:
        from actions.physical.movement import move_backward
        res = await move_backward(distance_mm=100.0)
        return str(res)
    except Exception as e:
        return f"Physical move_backward failed or robot not connected: {e}"


async def handle_turn_left(command: str = "", **kwargs) -> str:
    try:
        from actions.physical.movement import turn_left
        res = await turn_left(angle_degrees=90.0)
        return str(res)
    except Exception as e:
        return f"Physical turn_left failed or robot not connected: {e}"


async def handle_turn_right(command: str = "", **kwargs) -> str:
    try:
        from actions.physical.movement import turn_right
        res = await turn_right(angle_degrees=90.0)
        return str(res)
    except Exception as e:
        return f"Physical turn_right failed or robot not connected: {e}"


async def handle_turn_around(command: str = "", **kwargs) -> str:
    try:
        from actions.physical.movement import turn_around
        res = await turn_around()
        return str(res)
    except Exception as e:
        return f"Physical turn_around failed or robot not connected: {e}"


async def handle_stop_movement(command: str = "", **kwargs) -> str:
    try:
        from actions.physical.movement import stop_movement
        res = await stop_movement()
        return str(res)
    except Exception as e:
        return f"Physical stop_movement failed or robot not connected: {e}"


async def handle_dock_with_charger(command: str = "", **kwargs) -> str:
    try:
        from actions.physical.charger import dock_with_charger
        res = await dock_with_charger()
        return str(res)
    except Exception as e:
        return f"Physical dock_with_charger failed or robot not connected: {e}"


async def handle_arc_sweep(command: str = "", **kwargs) -> str:
    try:
        from actions.physical.movement import arc_sweep
        res = await arc_sweep()
        return str(res)
    except Exception as e:
        return f"Physical arc_sweep failed or robot not connected: {e}"


# -----------------------------------------------------------------------------
# Digital Setups Handlers
# -----------------------------------------------------------------------------
async def handle_setup_gaming(command: str = "", **kwargs) -> str:
    try:
        from actions.digital.setups import setup_gaming
        await setup_gaming()
        return "Gaming setup launched successfully."
    except Exception as e:
        return f"Failed to launch gaming setup: {e}"


async def handle_setup_study(command: str = "", **kwargs) -> str:
    try:
        from actions.digital.setups import setup_study
        await setup_study()
        return "Study setup launched successfully."
    except Exception as e:
        return f"Failed to launch study setup: {e}"


async def handle_setup_coding(command: str = "", **kwargs) -> str:
    try:
        from actions.digital.setups import setup_coding
        await setup_coding()
        return "Coding setup launched successfully."
    except Exception as e:
        return f"Failed to launch coding setup: {e}"


# -----------------------------------------------------------------------------
# System Tools Handlers
# -----------------------------------------------------------------------------
async def handle_tell_time(command: str = "", **kwargs) -> str:
    current_time = datetime.now().strftime("%I:%M %p")
    return f"The time is exactly {current_time}."


async def handle_get_date(command: str = "", **kwargs) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    return f"Today is {today}."


# -----------------------------------------------------------------------------
# Cognitive Agents Handlers
# -----------------------------------------------------------------------------
async def handle_calendar_node(command: str, **kwargs) -> str:
    try:
        from actions.digital.langgraph.calendar_agent import run_calendar_agent
        return run_calendar_agent(command)
    except Exception:
        from actions.digital.n8n_agents import call_n8n_calendar
        return call_n8n_calendar(command)


async def handle_weather_node(command: str, **kwargs) -> str:
    import re
    city = "Vienna"
    city_match = re.search(r'\bin\s+([A-Za-z\s]+)', command, re.IGNORECASE)
    if city_match:
        extracted = city_match.group(1).strip()
        if len(extracted.split()) <= 2:
            city = extracted

    from actions.digital.langchain.weather_agent import get_weather
    raw_weather = get_weather.func(city)

    weather_prompt = f"""You are Cozmo, a friendly robot assistant.
    Here is the raw weather data fetched for '{city}':
    "{raw_weather}"
    
    Based on this raw data, write a short, natural, conversational response that you can speak out loud.
    You MUST explicitly include the exact temperature in degrees (in Celsius).
    Keep it to a single friendly sentence.
    """
    response = chat_llm.invoke([
        SystemMessage(content="You are Cozmo. Write a friendly, single-sentence weather update."),
        HumanMessage(content=weather_prompt)
    ])
    return response.content.strip()


async def handle_web_search_node(command: str, **kwargs) -> str:
    try:
        from actions.digital.n8n_agents import call_web_search
        reply = call_web_search(command)
        if reply:
            return reply
    except Exception:
        pass

    try:
        from actions.digital.MCPs import fetch_tavily_search
        return await fetch_tavily_search(command)
    except Exception as e:
        return f"Web search could not be completed: {e}"


async def handle_code_executor_node(command: str, **kwargs) -> str:
    from actions.digital.langchain.code_executor import code_executor
    return code_executor(command)


async def handle_todolist_node(command: str, **kwargs) -> str:
    from actions.digital.langgraph.todolist_agent import run_todolist_agent
    return run_todolist_agent(command)


async def handle_none_chat(command: str, **kwargs) -> str:
    system_instructions = (
        "You are Cozmo, an advanced personal robot assistant. "
        "Be friendly, highly conversational, concise, and helpful (1-2 sentences max)."
    )
    response = chat_llm.invoke([
        SystemMessage(content=system_instructions),
        HumanMessage(content=command)
    ])
    return response.content.strip()


# Action dispatch map
BASELINE_ACTION_HANDLERS: Dict[str, Callable] = {
    "move_forward": handle_move_forward,
    "move_backward": handle_move_backward,
    "turn_left": handle_turn_left,
    "turn_right": handle_turn_right,
    "turn_around": handle_turn_around,
    "stop_movement": handle_stop_movement,
    "dock_with_charger": handle_dock_with_charger,
    "arc_sweep": handle_arc_sweep,
    "setup_gaming": handle_setup_gaming,
    "setup_study": handle_setup_study,
    "setup_coding": handle_setup_coding,
    "tell_time": handle_tell_time,
    "get_date": handle_get_date,
    "calendar_node": handle_calendar_node,
    "weather_node": handle_weather_node,
    "web_search_node": handle_web_search_node,
    "code_executor_node": handle_code_executor_node,
    "todolist_node": handle_todolist_node,
    "none": handle_none_chat,
}


async def dispatch_action(route_name: str, command: str = "", **kwargs) -> str:
    """Executes the chosen baseline action and returns the output string."""
    handler = BASELINE_ACTION_HANDLERS.get(route_name, handle_none_chat)
    if inspect.iscoroutinefunction(handler):
        return await handler(command=command, **kwargs)
    else:
        return handler(command=command, **kwargs)
