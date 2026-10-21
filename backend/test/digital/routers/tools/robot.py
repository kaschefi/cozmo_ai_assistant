# backend/test/digital/routers/tools/robot.py
"""
Namespace: robot.*
Physical robot controls, chassis kinematics, head/lift motors, and autonomous docking.
"""

from typing import Dict, List

ROBOT_NAMESPACE = "robot"

ROBOT_TOOLS: Dict[str, str] = {
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
    "arc_sweep": (
        "Executes a physical and visual scanning sweep of the surrounding area with camera and head tilt. "
        "Use when user commands the robot to scan the area, sweep arc, survey the room, or look around."
    ),
}

# Layer 1 Tool RAG specifications for physical robot actions
ROBOT_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": ROBOT_NAMESPACE}
    for name, desc in ROBOT_TOOLS.items()
]
