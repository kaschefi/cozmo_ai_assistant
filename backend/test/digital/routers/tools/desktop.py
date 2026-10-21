# backend/test/digital/routers/tools/desktop.py
"""
Namespace: desktop.*
Workstation presets, local OS automations, and system utilities.
"""

from typing import Dict, List

DESKTOP_NAMESPACE = "desktop"

DESKTOP_TOOLS: Dict[str, str] = {
    # -------------------------------------------------------------------------
    # Workstation Presets & App Launchers
    # -------------------------------------------------------------------------
    "setup_gaming": (
        "Launches PC video game applications (Steam, Counter-Strike, Discord) to play video games on the laptop."
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
    # System Utilities
    # -------------------------------------------------------------------------
    "tell_time": (
        "Provides the exact current local time. "
        "Use when user asks what time it is, tell me the time, current time, or what's the time right now."
    ),
    "get_date": (
        "Provides today's full date (day of week, month, day, year). "
        "Use when user asks what is today's date, what day it is today, or tell me the date."
    ),
}

# Layer 1 Tool RAG specifications for desktop tools
DESKTOP_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": DESKTOP_NAMESPACE}
    for name, desc in DESKTOP_TOOLS.items()
]
