# backend/test/digital/routers/tools/desktop.py
"""
Namespace: desktop.*
Workstation presets, local OS automations, display/audio/network toggles, power management, and system utilities.
Contains 20 desktop tools (5 base + 15 extended).
"""

from typing import Dict, List

DESKTOP_NAMESPACE = "desktop"

# -----------------------------------------------------------------------------
# Base Workstation Presets & System Utilities (Active in baseline MoKa)
# -----------------------------------------------------------------------------
DESKTOP_BASE_TOOLS: Dict[str, str] = {
    # Workstation Presets & App Launchers
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
    # System Utilities
    "tell_time": (
        "Provides the exact current local time. "
        "Use when user asks what time it is, tell me the time, current time, or what's the time right now."
    ),
    "get_date": (
        "Provides today's full date (day of week, month, day, year). "
        "Use when user asks what is today's date, what day it is today, or tell me the date."
    ),
}

# -----------------------------------------------------------------------------
# Extended Workstation & OS Automation Tools (Scaling to 100 tools)
# -----------------------------------------------------------------------------
DESKTOP_EXTRA_TOOLS: Dict[str, str] = {
    # --- Audio & Display ---
    "set_system_volume": (
        "Sets the laptop's master speaker volume to a level or raises or lowers it. "
        "Use when user says turn the computer volume up, down, or set laptop volume to a percentage."
    ),
    "mute_system_audio": (
        "Mutes or unmutes all sound output on the laptop. "
        "Use when user says mute the computer, silence the laptop, or unmute the sound."
    ),
    "adjust_screen_brightness": (
        "Raises or lowers the laptop screen brightness. "
        "Use when user says the screen is too bright, too dark, dim the display, or set brightness."
    ),
    "toggle_dark_mode": (
        "Switches the operating system between dark theme and light theme. "
        "Use when user wants dark mode, light mode, or to change the system theme."
    ),
    "take_screenshot": (
        "Captures a screenshot of the laptop screen and saves it to the pictures folder. "
        "Use when user says take a screenshot, capture the screen, or screen grab."
    ),
    # --- Power & Session ---
    "lock_screen": (
        "Locks the laptop session so a password is required to continue. "
        "Use when user says lock the computer, lock my screen, or I'm stepping away."
    ),
    "put_computer_to_sleep": (
        "Puts the laptop into sleep or suspend mode. "
        "Use when user says sleep the computer, suspend the laptop, or hibernate."
    ),
    "shutdown_computer": (
        "Shuts down or restarts the laptop after confirmation. "
        "Use when user says shut down the computer, power off the laptop, or restart the PC."
    ),
    # --- Apps ---
    "open_application": (
        "Launches a named desktop application such as Spotify, Chrome, VS Code, Notepad, or Calculator. "
        "Use when user says open, launch, or start a specific program."
    ),
    "close_application": (
        "Closes or force quits a running desktop application by name. "
        "Use when user says close, quit, exit, or kill a specific program."
    ),
    # --- Connectivity & Focus ---
    "toggle_wifi": (
        "Turns the laptop Wi-Fi adapter on or off. "
        "Use when user says enable wifi, disable wifi, or turn off the wireless connection."
    ),
    "toggle_bluetooth": (
        "Turns the laptop Bluetooth adapter on or off. "
        "Use when user says turn Bluetooth on, turn Bluetooth off, or enable Bluetooth."
    ),
    "toggle_do_not_disturb": (
        "Enables or disables the operating system Do Not Disturb or Focus Assist mode to silence notifications. "
        "Use when user says do not disturb, mute notifications, or focus mode on the computer."
    ),
    # --- Diagnostics & Presets ---
    "get_system_stats": (
        "Reports laptop CPU usage, RAM usage, disk space, and laptop battery percentage. "
        "Use when user asks how the computer is performing, how much memory is free, or laptop battery level."
    ),
    "setup_meeting": (
        "Prepares the workstation for a video call by opening the meeting app, muting notifications, and checking webcam and microphone. "
        "Use when user says set up for a meeting, prepare for a call, or meeting mode."
    ),
}

# Unified 20 desktop tools dictionary
DESKTOP_TOOLS: Dict[str, str] = {
    **DESKTOP_BASE_TOOLS,
    **DESKTOP_EXTRA_TOOLS,
}

# Layer 1 Tool RAG specifications for desktop tools
DESKTOP_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": DESKTOP_NAMESPACE}
    for name, desc in DESKTOP_TOOLS.items()
]

# Backward-compatibility alias
DESKTOP_EXTRA_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": DESKTOP_NAMESPACE}
    for name, desc in DESKTOP_EXTRA_TOOLS.items()
]
