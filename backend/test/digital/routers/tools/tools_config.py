# backend/test/digital/routers/tools/tools_config.py
"""
Aggregated Tools Configuration for Router Benchmarking.

Imports partitioned tool definitions from all 8 domain namespaces:
- robot.* (Physical chassis kinematics, head, lift, docking, scanning, Cozmo actions)
- desktop.* (Workstation presets, local apps, OS utilities, display, power)
- cognitive.* (Search, calendar, math sandbox, weather, tasks, email, maps, translation, summarizer, contacts)
- media.* (Spotify playback, YouTube, playlist, artist, volume, podcast)
- smart_home.* (Philips Hue lights, brightness, scenes, thermostat, plugs, locks, blinds)
- companion.* (Speed tap, memory match, jokes, dances, emotion animations)
- comms.* (SMS, phone calls, Discord, video meetings, notifications)
- productivity.* (Timers, alarms, reminders, pomodoro, quick notes)

Gathers all definitions into unified registries (TOOLS_15, TOOLS_18, TOOLS_20, TOOLS_30, TOOLS_50, TOOLS_100)
and provides scaling utilities for the Bachelor's Thesis benchmark experiments.
"""

from typing import Dict, Any, List, Optional

# -----------------------------------------------------------------------------
# Import all 8 Domain Namespaces
# -----------------------------------------------------------------------------
from test.digital.routers.tools.robot import (
    ROBOT_NAMESPACE,
    ROBOT_TOOLS,
    ROBOT_BASE_TOOLS,
    ROBOT_RAG_SPECS,
)
from test.digital.routers.tools.desktop import (
    DESKTOP_NAMESPACE,
    DESKTOP_TOOLS,
    DESKTOP_BASE_TOOLS,
    DESKTOP_RAG_SPECS,
)
from test.digital.routers.tools.cognitive import (
    COGNITIVE_NAMESPACE,
    COGNITIVE_TOOLS,
    COGNITIVE_BASE_TOOLS,
    COGNITIVE_RAG_SPECS,
    CODE_EXECUTOR_DIMENSIONS,
)
from test.digital.routers.tools.media import (
    MEDIA_NAMESPACE,
    MEDIA_TOOLS,
    MEDIA_RAG_SPECS,
)
from test.digital.routers.tools.smart_home import (
    SMART_HOME_NAMESPACE,
    SMART_HOME_TOOLS,
    SMART_HOME_RAG_SPECS,
)
from test.digital.routers.tools.companion import (
    COMPANION_NAMESPACE,
    COMPANION_TOOLS,
    COMPANION_RAG_SPECS,
)
from test.digital.routers.tools.comms import (
    COMMS_NAMESPACE,
    COMMS_TOOLS,
    COMMS_RAG_SPECS,
)
from test.digital.routers.tools.productivity import (
    PRODUCTIVITY_NAMESPACE,
    PRODUCTIVITY_TOOLS,
    PRODUCTIVITY_RAG_SPECS,
)

# -----------------------------------------------------------------------------
# Conversational Fallback Channel
# Note: 'jokes' removed so requests for jokes cleanly route to companion.tell_joke
# -----------------------------------------------------------------------------
FALLBACK_ROUTE: Dict[str, str] = {
    "none": (
        "Core conversational channel. Use for casual chat, greetings, social pleasantries, asking about "
        "identity/personality, sharing personal facts or hobbies, philosophical discussion, or small talk."
    ),
}

# -----------------------------------------------------------------------------
# Core Baseline Tool Subsets (15 & 18 tools)
# -----------------------------------------------------------------------------

# Unified 18 Core Active Tools (+ 'none' fallback = 19 routes total)
TOOLS_18: Dict[str, str] = {
    **ROBOT_BASE_TOOLS,      # 8 tools
    **DESKTOP_BASE_TOOLS,    # 5 tools
    **COGNITIVE_BASE_TOOLS,  # 5 tools
    **FALLBACK_ROUTE,
}

# Backward-compatible 15 Core Tools subset (used in initial WP2 48-case benchmark)
TOOLS_15: Dict[str, str] = {
    k: v for k, v in TOOLS_18.items()
    if k not in ("arc_sweep", "code_executor_node", "todolist_node")
}

# -----------------------------------------------------------------------------
# Master 100 Tools Dictionary
# Aggregates all 100 unique tools across all 8 domain namespaces
# -----------------------------------------------------------------------------
TOOLS_100_WITHOUT_FALLBACK: Dict[str, str] = {
    **ROBOT_TOOLS,           # 26 tools
    **DESKTOP_TOOLS,         # 20 tools
    **COGNITIVE_TOOLS,       # 10 tools
    **MEDIA_TOOLS,           # 14 tools
    **SMART_HOME_TOOLS,      # 12 tools
    **COMPANION_TOOLS,       # 6 tools
    **COMMS_TOOLS,           # 5 tools
    **PRODUCTIVITY_TOOLS,    # 7 tools
}

# Full 100 tools + 'none' fallback channel
TOOLS_100: Dict[str, str] = {
    **TOOLS_100_WITHOUT_FALLBACK,
    **FALLBACK_ROUTE,
}

# Master alias
TOOLS_ALL: Dict[str, str] = TOOLS_100

# -----------------------------------------------------------------------------
# Scaling Presets for Bachelor's Thesis Experiments (N = 20, 30, 50, 100)
# -----------------------------------------------------------------------------
# N = 20: 18 base tools + 2 essential media tools
_PRESET_20_KEYS = list(TOOLS_18.keys()) + ["spotify_play_playlist", "youtube_play_video"]
TOOLS_20: Dict[str, str] = {
    k: TOOLS_100[k] for k in _PRESET_20_KEYS if k in TOOLS_100
}

# N = 30: 20 tools + 10 smart home tools
_PRESET_30_KEYS = _PRESET_20_KEYS + [
    "lights_on", "lights_off", "set_light_brightness", "set_light_color",
    "activate_light_scene", "set_thermostat", "get_indoor_temperature",
    "turn_on_smart_plug", "turn_off_smart_plug", "lock_door"
]
TOOLS_30: Dict[str, str] = {
    k: TOOLS_100[k] for k in _PRESET_30_KEYS if k in TOOLS_100
}

# N = 50: 30 tools + 20 additional tools from desktop, cognitive, and productivity
_PRESET_50_KEYS = _PRESET_30_KEYS + [
    # Desktop extra (10)
    "set_system_volume", "mute_system_audio", "adjust_screen_brightness", "toggle_dark_mode",
    "take_screenshot", "lock_screen", "put_computer_to_sleep", "shutdown_computer",
    "open_application", "setup_meeting",
    # Cognitive extra (5)
    "gmail_node", "maps_directions_node", "translation_node", "summarizer_node", "contacts_node",
    # Productivity (5)
    "set_timer", "set_alarm", "cancel_alarm", "create_reminder", "start_pomodoro"
]
TOOLS_50: Dict[str, str] = {
    k: TOOLS_100[k] for k in _PRESET_50_KEYS if k in TOOLS_100
}


def get_tools_preset(n: int, include_fallback: bool = True) -> Dict[str, str]:
    """
    Returns deterministic tool dictionary for standardized benchmark scaling runs:
    n in [15, 18, 20, 30, 50, 100].
    """
    preset_map = {
        15: TOOLS_15,
        18: TOOLS_18,
        20: TOOLS_20,
        30: TOOLS_30,
        50: TOOLS_50,
        100: TOOLS_100,
    }
    if n not in preset_map:
        # Fall back to arbitrary slice
        ordered_keys = list(TOOLS_100_WITHOUT_FALLBACK.keys())[:n]
        tools = {k: TOOLS_100_WITHOUT_FALLBACK[k] for k in ordered_keys}
        if include_fallback:
            tools["none"] = FALLBACK_ROUTE["none"]
        return tools

    tools = dict(preset_map[n])
    if not include_fallback and "none" in tools:
        del tools["none"]
    return tools


def get_tools_subset(n: Optional[int] = None, include_fallback: bool = True) -> Dict[str, str]:
    """Helper to get any subset of size n (or full 100 tools if n is None)."""
    if n is None or n >= 100:
        return get_tools_preset(100, include_fallback=include_fallback)
    return get_tools_preset(n, include_fallback=include_fallback)


# -----------------------------------------------------------------------------
# Hierarchical Domain Namespacing (Phase 2 Scaling Foundation)
# Maps domain keys to their partitioned tool subsets
# -----------------------------------------------------------------------------
TOOL_NAMESPACES: Dict[str, Dict[str, str]] = {
    ROBOT_NAMESPACE: ROBOT_TOOLS,
    DESKTOP_NAMESPACE: DESKTOP_TOOLS,
    COGNITIVE_NAMESPACE: COGNITIVE_TOOLS,
    MEDIA_NAMESPACE: MEDIA_TOOLS,
    SMART_HOME_NAMESPACE: SMART_HOME_TOOLS,
    COMPANION_NAMESPACE: COMPANION_TOOLS,
    COMMS_NAMESPACE: COMMS_TOOLS,
    PRODUCTIVITY_NAMESPACE: PRODUCTIVITY_TOOLS,
}

# -----------------------------------------------------------------------------
# Layer 1 Tool RAG Indexing Specifications (Multi-Document Registry)
# Gathers all 104 raw documents for FAISS indexing across all namespaces.
# -----------------------------------------------------------------------------
TOOL_RAG_REGISTRY_SPECS: List[Dict[str, str]] = (
    ROBOT_RAG_SPECS
    + DESKTOP_RAG_SPECS
    + COGNITIVE_RAG_SPECS
    + MEDIA_RAG_SPECS
    + SMART_HOME_RAG_SPECS
    + COMPANION_RAG_SPECS
    + COMMS_RAG_SPECS
    + PRODUCTIVITY_RAG_SPECS
)


def build_laya_questions(tools_dict: Dict[str, str] = TOOLS_18) -> Dict[str, Any]:
    """
    Builds the typed choice question dictionary required by Laya.
    Accepts any candidate subset (e.g. Top-K from FAISS, or full N tools).
    """
    return {
        "tool_selection": {
            "type": "choice",
            "instructions": (
                "Select the appropriate tool or service to handle the user's request, question, or command. "
                "Use 'web_search_node' whenever the user wants to look up information, search the web, check company market data, sports results, or news. "
                "Select 'none' only if the user is simply chatting, greeting, sharing personal facts, or making casual small talk."
            ),
            "criteria": tools_dict,
        }
    }


def register_all_tools_to_rag(registry=None, specs: Optional[List[Dict[str, str]]] = None):
    """
    Registers system tools into the Layer 1 FAISS ToolVectorRegistry.
    Defaults to all 104 specs across all 100 tools.
    """
    if registry is None:
        from core.routing.layer2.tool_vector_db import tool_rag_registry
        registry = tool_rag_registry

    target_specs = specs if specs is not None else TOOL_RAG_REGISTRY_SPECS
    for spec in target_specs:
        registry.register_tool_schema(name=spec["name"], description=spec["description"])
