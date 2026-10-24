# backend/test/digital/routers/tools/__init__.py
"""
Tools package organizing partitioned tool definitions by domain namespaces:
- robot.* (Physical kinematics, docking, Cozmo actions)
- desktop.* (Workstation setups, system tools, OS controls)
- cognitive.* (Sub-agents: search, calendar, weather, code, todoist, email, maps, translation, etc.)
- media.* (Spotify & multimedia controls)
- smart_home.* (IoT & home automation)
- companion.* (Games, dances, jokes, emotional animations)
- comms.* (SMS, calls, Discord, meetings, notifications)
- productivity.* (Timers, alarms, reminders, pomodoro, notes)
"""

from test.digital.routers.tools.tools_config import (
    TOOLS_15,
    TOOLS_18,
    TOOLS_20,
    TOOLS_30,
    TOOLS_50,
    TOOLS_100,
    TOOLS_ALL,
    FALLBACK_ROUTE,
    TOOL_NAMESPACES,
    TOOL_RAG_REGISTRY_SPECS,
    CODE_EXECUTOR_DIMENSIONS,
    build_laya_questions,
    register_all_tools_to_rag,
    get_tools_preset,
    get_tools_subset,
)
from test.digital.routers.tools.robot import ROBOT_TOOLS, ROBOT_NAMESPACE
from test.digital.routers.tools.desktop import DESKTOP_TOOLS, DESKTOP_NAMESPACE
from test.digital.routers.tools.cognitive import COGNITIVE_TOOLS, COGNITIVE_NAMESPACE
from test.digital.routers.tools.media import MEDIA_TOOLS, MEDIA_NAMESPACE
from test.digital.routers.tools.smart_home import SMART_HOME_TOOLS, SMART_HOME_NAMESPACE
from test.digital.routers.tools.companion import COMPANION_TOOLS, COMPANION_NAMESPACE
from test.digital.routers.tools.comms import COMMS_TOOLS, COMMS_NAMESPACE
from test.digital.routers.tools.productivity import PRODUCTIVITY_TOOLS, PRODUCTIVITY_NAMESPACE
from test.digital.routers.tools.registry import ALL_TOOLS_DICT, ALL_RAG_SPECS, unique_tool_names
