# backend/test/digital/routers/tools/__init__.py
"""
Tools package organizing partitioned tool definitions by domain namespaces:
- robot.* (Physical kinematics & docking)
- desktop.* (Workstation setups & system tools)
- cognitive.* (Sub-agents: search, calendar, weather, code, todoist)
- media.* (Spotify & multimedia controls)
- smart_home.* (IoT & home automation)
"""

from test.digital.routers.tools.tools_config import (
    TOOLS_18,
    TOOLS_15,
    TOOLS_ALL,
    TOOL_NAMESPACES,
    TOOL_RAG_REGISTRY_SPECS,
    CODE_EXECUTOR_DIMENSIONS,
    build_laya_questions,
    register_all_tools_to_rag,
)
from test.digital.routers.tools.robot import ROBOT_TOOLS, ROBOT_NAMESPACE
from test.digital.routers.tools.desktop import DESKTOP_TOOLS, DESKTOP_NAMESPACE
from test.digital.routers.tools.cognitive import COGNITIVE_TOOLS, COGNITIVE_NAMESPACE
from test.digital.routers.tools.media import MEDIA_TOOLS, MEDIA_NAMESPACE
from test.digital.routers.tools.smart_home import SMART_HOME_TOOLS, SMART_HOME_NAMESPACE
