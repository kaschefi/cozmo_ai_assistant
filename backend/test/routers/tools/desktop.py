# backend/test/routers/tools/desktop.py
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
        "Prepares the workstation for university study by opening browser tabs for Moodle and NotebookLM. "
        "Use when user says they want to study, activate study mode, or prepare for university homework and coursework."
    ),
    "setup_coding": (
        "Prepares the development workspace by opening GitHub and launching PyCharm IDE. "
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
        "Adjusts the computer or laptop master OS audio speaker volume level up or down. "
        "Use when user says make the PC louder, turn the computer volume up, lower laptop volume, or set laptop volume to a percentage."
    ),
    "mute_system_audio": (
        "Mutes or unmutes all audio sound output on the laptop or PC. "
        "Use when user says mute the computer audio, silence laptop sound output, unmute the PC speakers, or toggle audio mute on the computer."
    ),
    "adjust_screen_brightness": (
        "Adjusts the computer monitor display screen brightness level. "
        "Use when user says the screen is too bright or dark, dim the laptop screen or display, brighten the monitor, or change display brightness. "
        "Controls computer screen backlight, not physical room lights."
    ),
    "toggle_dark_mode": (
        "Switches operating system desktop appearance theme between dark mode and light mode for Windows and application windows. "
        "Use when user wants dark mode, light theme, or to toggle dark and light system appearance."
    ),
    "take_screenshot": (
        "Captures a digital screenshot or screen grab of the desktop monitor display or active window and saves the image to files. "
        "Use when user says take a screenshot, capture the desktop display, grab a screen capture, or save screen image. "
        "Captures the computer PC display, not a robot camera photo."
    ),
    # --- Power & Session ---
    "lock_screen": (
        "Locks the computer desktop workstation session requiring a password or PIN to continue. "
        "Use when user says lock my computer screen, lock the laptop session for security, lock the PC, or stepping away from desk."
    ),
    "put_computer_to_sleep": (
        "Puts the laptop or desktop computer into operating system sleep, standby, or suspend mode. "
        "Use when user says put the laptop to sleep, suspend the computer, put the PC into sleep mode, or sleep the computer. "
        "Controls computer OS power state, not physical robot docking."
    ),
    "shutdown_computer": (
        "Powers off, shuts down, or restarts the laptop or desktop computer operating system. "
        "Use when user says shut down my laptop completely, power off the computer, restart the PC, or reboot workstation."
    ),
    # --- Apps ---
    "open_application": (
        "Launches or opens a specific desktop software application or program on the laptop (such as Calculator, Google Chrome, Notepad text editor). "
        "Use when user says open, launch, or start a specific desktop program."
    ),
    "close_application": (
        "Closes, quits, or force terminates a running desktop application window or program on the PC (such as closing Chrome, quitting Spotify, or force quitting Calculator). "
        "Use when user says close, quit, exit, or kill a specific desktop application."
    ),
    # --- Connectivity & Focus ---
    "toggle_wifi": (
        "Turns the laptop Wi-Fi wireless network adapter connection on or off. "
        "Use when user says turn off Wi-Fi on laptop, enable wireless network, or disconnect from Wi-Fi on this PC."
    ),
    "toggle_bluetooth": (
        "Turns the computer Bluetooth radio adapter on or off. "
        "Use when user says turn on Bluetooth, enable Bluetooth to connect headphones, or disable laptop Bluetooth."
    ),
    "toggle_do_not_disturb": (
        "Enables or disables operating system Focus Assist or Do Not Disturb notification mode on the laptop. "
        "Use when user says turn on Do Not Disturb mode on laptop, mute Windows desktop notifications to focus, or disable Focus Assist."
    ),
    # --- Diagnostics & Presets ---
    "get_system_stats": (
        "Reports computer hardware performance diagnostics including CPU utilization, RAM memory usage, free disk storage, and laptop battery percentage. "
        "Use when user asks how much RAM/CPU is used, checks disk space, or asks laptop battery level."
    ),
    "setup_meeting": (
        "Prepares workstation for a video conference call by launching meeting software (Zoom, Teams, Google Meet), muting background desktop alerts, and verifying webcam and microphone. "
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
