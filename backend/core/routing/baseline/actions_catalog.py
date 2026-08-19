# backend/core/routing/baseline/actions_catalog.py
"""
Exhaustive catalog of all available actions across the MoKa AI Assistant system.
This file serves as the single source of truth for the baseline router, which gives
every action and description to the LLM in a single prompt.
"""

from typing import Dict, Any, List

ALL_ACTIONS_CATALOG: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Physical Robot Actions
    # -------------------------------------------------------------------------
    "move_forward": {
        "category": "physical",
        "description": "Drives the Cozmo robot forward by a specified distance (e.g. 100mm). Use when the user commands the robot to move forward, drive forward, go forward, or step forward.",
        "examples": ["move forward", "go forward", "drive forward", "step forward 10cm"],
    },
    "move_backward": {
        "category": "physical",
        "description": "Drives the Cozmo robot backward by a specified distance. Use when the user commands the robot to move backward, drive backward, go back, or back up.",
        "examples": ["move backward", "drive back", "go backward", "step back"],
    },
    "turn_left": {
        "category": "physical",
        "description": "Rotates the Cozmo robot 90 degrees to the left. Use when the user commands the robot to turn left, rotate left, spin left, or look left.",
        "examples": ["turn left", "rotate left", "spin left", "look left"],
    },
    "turn_right": {
        "category": "physical",
        "description": "Rotates the Cozmo robot 90 degrees to the right. Use when the user commands the robot to turn right, rotate right, spin right, or look right.",
        "examples": ["turn right", "rotate right", "spin right", "look right"],
    },
    "turn_around": {
        "category": "physical",
        "description": "Rotates the Cozmo robot 180 degrees to face the opposite direction. Use when the user commands the robot to turn around, spin around, do a 180, or about-face.",
        "examples": ["turn around", "spin around", "do a 180", "about face"],
    },
    "stop_movement": {
        "category": "physical",
        "description": "Immediately halts all motors and emergency stops any active robot movement. Use when the user commands the robot to stop, halt, freeze, stop moving, or brake.",
        "examples": ["stop", "halt", "freeze", "stop moving", "break", "emergency stop"],
    },
    "dock_with_charger": {
        "category": "physical",
        "description": "Initiates autonomous camera-guided visual marker search and physical docking onto the charging base. Use when the user tells the robot to dock, go to charger, go to sleep, battery is low, or return to base.",
        "examples": ["go to sleep", "go to your charger", "dock yourself", "your battery is low", "return to base", "find the charger"],
    },
    "arc_sweep": {
        "category": "physical",
        "description": "Executes a visual and physical scanning sweep of the surrounding area. Use when the user commands the robot to scan the area, sweep arc, look around, or observe surroundings.",
        "examples": ["scan area", "sweep arc", "look around", "observe surroundings"],
    },

    # -------------------------------------------------------------------------
    # Digital Setups & OS Automation
    # -------------------------------------------------------------------------
    "setup_gaming": {
        "category": "digital_setup",
        "description": "Launches the gaming environment on the laptop, opening Steam, CS2, and Discord. Use when the user wants to play games, activate gaming mode, or open gaming apps.",
        "examples": ["set my laptop for gaming", "gaming mode", "open steam and discord", "time to game", "prepare for gaming", "gaming work"],
    },
    "setup_study": {
        "category": "digital_setup",
        "description": "Prepares the study workstation by opening browser tabs for Moodle, Google Gemini, Google NotebookLM, and YouTube. Use when the user wants to study, activate study mode, or open study resources.",
        "examples": ["set it for study", "study mode", "time to study", "prepare my laptop for study", "open my study tabs", "study work"],
    },
    "setup_coding": {
        "category": "digital_setup",
        "description": "Prepares the development workspace by opening browser tabs for GitHub, Google Gemini, YouTube, and launching PyCharm IDE. Use when the user wants to code, activate coding mode, or prepare for programming.",
        "examples": ["set it for coding", "set my laptop for coding", "coding mode", "time to code", "prepare for coding", "setups code"],
    },

    # -------------------------------------------------------------------------
    # Digital System Tools
    # -------------------------------------------------------------------------
    "tell_time": {
        "category": "system",
        "description": "Provides the exact current local time. Use when the user asks what time it is, tell me the time, current time, or what's the time right now.",
        "examples": ["what time is it", "tell me the time", "current time", "what's the time right now"],
    },
    "get_date": {
        "category": "system",
        "description": "Provides today's full date (day of week, month, day, year). Use when the user asks what is today's date, what day is it today, or tell me the date.",
        "examples": ["what is the date", "what is today", "tell me the date", "what day is it today"],
    },

    # -------------------------------------------------------------------------
    # Digital Cognitive Tools / Sub-Agents
    # -------------------------------------------------------------------------
    "calendar_node": {
        "category": "cognitive_agent",
        "description": "Manages Google Calendar operations. Use this if the user wants to check, create, schedule, move, reschedule, change, or delete meetings, events, appointments, or check for scheduling conflicts.",
        "examples": [
            "schedule a meeting with Bob tomorrow at 3pm",
            "what is on my calendar for Friday?",
            "cancel my dentist appointment",
            "move my 2pm meeting to 4pm",
            "do I have any events this afternoon?"
        ],
    },
    "weather_node": {
        "category": "cognitive_agent",
        "description": "Provides real-time weather conditions, forecasts, temperatures (in Celsius), precipitation, rain, snow, storm, or wind reports for any specified city (defaults to Vienna).",
        "examples": [
            "what is the weather like today?",
            "how warm is it in Paris?",
            "is it going to rain tomorrow in Vienna?",
            "give me the current temperature outside"
        ],
    },
    "web_search_node": {
        "category": "cognitive_agent",
        "description": "Searches the live web for general real-time information, breaking news, sports scores, stock prices, recent events, or external factual knowledge that changes over time.",
        "examples": [
            "who won the Champions League yesterday?",
            "what is the latest stock price of Apple?",
            "what happened in the news today?",
            "search for recent developments in quantum computing"
        ],
    },
    "code_executor_node": {
        "category": "cognitive_agent",
        "description": "Executes Python code in an isolated sandbox for exact mathematical calculations, arithmetic, algebra, percentages, geometry, logic puzzles, coordinate navigation, data filtering/sorting, string manipulation, or reversing words.",
        "examples": [
            "calculate 458 * 932",
            "what is the square root of 5041?",
            "spell the word 'elephant' backwards",
            "sort this list of numbers: [4, 1, 9, 2]",
            "how many days are between March 15 and August 22?"
        ],
    },
    "todolist_node": {
        "category": "cognitive_agent",
        "description": "Manages Todoist tasks and to-do lists. Use when the user wants to add a task, check off/complete a task, delete a task, list active tasks, or organize project to-dos.",
        "examples": [
            "add buy milk to my todo list",
            "what tasks do I have today?",
            "mark bake a cake as done",
            "delete the task call mom"
        ],
    },

    # -------------------------------------------------------------------------
    # Conversational Fallback
    # -------------------------------------------------------------------------
    "none": {
        "category": "conversational",
        "description": "Core conversational channel. Use for casual chat, greetings, asking about identity/personality, sharing personal facts or hobbies, jokes, philosophical discussion, or anything not requiring an action or tool above.",
        "examples": [
            "hello, how are you today?",
            "my name is Alex and I like playing guitar",
            "tell me something interesting",
            "what do you think about AI?",
            "thanks for your help"
        ],
    }
}


def get_all_action_names() -> List[str]:
    """Returns a list of all action names in the catalog."""
    return list(ALL_ACTIONS_CATALOG.keys())


def build_action_menu_string() -> str:
    """
    Formats all actions into a comprehensive description block to be injected
    directly into the monolithic baseline LLM system prompt.
    """
    lines = []
    for name, data in ALL_ACTIONS_CATALOG.items():
        lines.append(f'- "{name}": {data["description"]}')
    return "\n".join(lines)
