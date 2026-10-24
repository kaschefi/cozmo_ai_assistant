# backend/test/digital/routers/tools/productivity.py
"""
Namespace: productivity.*
Timers, alarms, reminders, focus sessions, and quick notes.
"""

from typing import Dict, List

PRODUCTIVITY_NAMESPACE = "productivity"

PRODUCTIVITY_TOOLS: Dict[str, str] = {
    "set_timer": (
        "Starts a countdown timer for a given duration. "
        "Use when user says set a timer for 10 minutes, countdown, or time this for me."
    ),
    "set_alarm": (
        "Sets a wake-up or alarm at a specific clock time. "
        "Use when user says wake me up at 7, set an alarm, or alarm for tomorrow morning."
    ),
    "cancel_alarm": (
        "Cancels, disables, or deletes an existing alarm or running timer. "
        "Use when user says cancel my alarm, turn off the timer, or never mind the alarm."
    ),
    "create_reminder": (
        "Creates a one-time notification reminder at a specific time or after a delay, separate from calendar events and Todoist tasks. "
        "Use when user says remind me to do something in an hour or remind me at 5 pm."
    ),
    "start_pomodoro": (
        "Starts a Pomodoro focus session with 25-minute work intervals and short breaks. "
        "Use when user says start a pomodoro, focus session, or work sprint."
    ),
    "take_note": (
        "Saves a quick free-text note or idea to the personal notes list. "
        "Use when user says write this down, take a note, jot down, or save this idea."
    ),
    "read_notes": (
        "Reads back or searches previously saved personal notes. "
        "Use when user says what notes did I save, read my notes, or find my note about something."
    ),
}

PRODUCTIVITY_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": PRODUCTIVITY_NAMESPACE}
    for name, desc in PRODUCTIVITY_TOOLS.items()
]
