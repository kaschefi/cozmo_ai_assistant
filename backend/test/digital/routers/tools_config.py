# backend/test/digital/routers/tools_config.py
"""
Tools Configuration for Router Benchmarking.

Defines the 15 system actions and tools along with conversational fallback ("none")
to be tested across both the 2-Layer (Reflex + Laya) and 1-Layer (Monolithic Laya) architectures.
"""

from typing import Dict, Any

# 15 Core Tools across Physical, OS Setups, System Utilities, and Cognitive Agents
# (plus "none" for casual conversation fallback)
TOOLS_15: Dict[str, str] = {
    # -------------------------------------------------------------------------
    # Physical Robot Controls (7 tools)
    # -------------------------------------------------------------------------
    "move_forward": (
        "Drives or rolls the Cozmo robot forward by a specified distance. "
        "Use when user commands the robot to move forward, crawl forward, advance, or drive ahead."
    ),
    "move_backward": (
        "Drives, rolls, or reverses the Cozmo robot backward. "
        "Use when user commands the robot to move backward, back up, reverse position, or drive back."
    ),
    "turn_left": (
        "Rotates or pivots the Cozmo robot 90 degrees to the left (counterclockwise). "
        "Use when user commands the robot to turn left, pivot left, or look left."
    ),
    "turn_right": (
        "Rotates or pivots the Cozmo robot 90 degrees to the right (clockwise). "
        "Use when user commands the robot to turn right, pivot right, or look right."
    ),
    "turn_around": (
        "Rotates the Cozmo robot 180 degrees to face backwards. "
        "Use when user commands the robot to turn around, face the wall behind, do a 180, or flip heading."
    ),
    "stop_movement": (
        "Immediately halts all motors and emergency stops any active robot movement. "
        "Use when user commands the robot to stop, halt, freeze, stand still, or brake."
    ),
    "dock_with_charger": (
        "Initiates autonomous physical docking onto the charging base. "
        "Use when user tells the robot to dock, go to charger, go to sleep, battery is low, or return to base."
    ),

    # -------------------------------------------------------------------------
    # OS Setups & Digital Automation (3 tools)
    # -------------------------------------------------------------------------
    "setup_gaming": (
        "Launches the gaming environment on the laptop, opening Steam, CS2, and Discord. "
        "Use when user wants to play games, activate gaming mode, or open gaming apps."
    ),
    "setup_study": (
        "Prepares the study workstation by opening browser tabs for Moodle, Gemini, NotebookLM, and YouTube. "
        "Use when user wants to study, activate study mode, or open study resources."
    ),
    "setup_coding": (
        "Prepares the development workspace by opening GitHub, Gemini, YouTube, and launching PyCharm IDE. "
        "Use when user wants to code, activate coding mode, or prepare for programming."
    ),

    # -------------------------------------------------------------------------
    # System Tools (2 tools)
    # -------------------------------------------------------------------------
    "tell_time": (
        "Provides the exact current local time. "
        "Use when user asks what time it is, tell me the time, current time, or what's the time right now."
    ),
    "get_date": (
        "Provides today's full date (day of week, month, day, year). "
        "Use when user asks what is today's date, what day is it today, or tell me the date."
    ),

    # -------------------------------------------------------------------------
    # Cognitive Sub-Agents (3 tools)
    # -------------------------------------------------------------------------
    "calendar_node": (
        "Manages Google Calendar operations. "
        "Use this if user wants to check, create, schedule, move, reschedule, change, or delete meetings, events, or appointments."
    ),
    "weather_node": (
        "Provides real-time weather conditions, forecasts, and temperatures (Celsius) for any specified city. "
        "Use for rain, temperature, outside conditions, or weather forecasts."
    ),
    "web_search_node": (
        "Searches the live web for real-time information, sports match results, sports scores, recent news, stock market prices, or current events. "
        "Use when user asks about winners of recent matches, current stock prices, or live web news."
    ),

    # -------------------------------------------------------------------------
    # Conversational Fallback (1 route)
    # -------------------------------------------------------------------------
    "none": (
        "Core conversational channel. Use for casual chat, greetings, asking about identity/personality, "
        "sharing personal facts or hobbies, jokes, philosophical discussion, or anything not requiring an action or tool."
    ),
}


def build_laya_questions(tools_dict: Dict[str, str] = TOOLS_15) -> Dict[str, Any]:
    """
    Builds the typed choice question dictionary required by Laya.
    """
    return {
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
