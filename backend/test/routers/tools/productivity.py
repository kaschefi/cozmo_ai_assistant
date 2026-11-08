# backend/test/routers/tools/productivity.py
"""
Namespace: productivity.*
Timers, alarms, reminders, focus sessions, and quick notes.
"""

from typing import Dict, List

PRODUCTIVITY_NAMESPACE = "productivity"

PRODUCTIVITY_TOOLS: Dict[str, str] = {
    "set_timer": (
        "Starts a countdown timer for a given duration. "
        "Use when user says set a timer for fifteen minutes, countdown forty-five seconds, or start a twenty-minute kitchen timer."
    ),
    "set_alarm": (
        "Sets a wake-up or alarm alert at a specific clock time. "
        "Use when user says set an alarm for seven-thirty tomorrow morning, wake me up at six AM sharp, or schedule an alarm clock alert for eight in the morning. "
        "Distinct from calendar meeting appointments."
    ),
    "cancel_alarm": (
        "Cancels, disables, or stops an active alarm clock alert or running countdown timer. "
        "Use when user says cancel my seven AM alarm, turn off the running kitchen countdown timer, or disable all active morning alarms."
    ),
    "create_reminder": (
        "Creates a one-time notification reminder alert at a specific time or after a delay. "
        "Use when user says remind me in two hours to drink water, set a reminder for five PM to take out the trash, or remind me after thirty minutes to check the oven (distinct from calendar events and Todoist tasks)."
    ),
    "start_pomodoro": (
        "Starts a Pomodoro focus session with 25-minute work intervals and short breaks. "
        "Use when user says start a pomodoro session, begin a twenty-five minute focus work interval, or start pomodoro productivity timer with short breaks."
    ),
    "take_note": (
        "Saves a quick free-text note or idea to the personal scratchpad notes list. "
        "Use when user says take a quick note, jot down this idea, or write this down in my personal notes list (distinct from Todoist task checklist items)."
    ),
    "read_notes": (
        "Reads back, lists, or searches previously saved personal scratchpad notes. "
        "Use when user says read back my saved notes from this week, what notes do I have stored about my thesis, or search my personal notes."
    ),
}

PRODUCTIVITY_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": PRODUCTIVITY_NAMESPACE}
    for name, desc in PRODUCTIVITY_TOOLS.items()
]
