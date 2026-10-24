# backend/test/digital/routers/tools/robot.py
"""
Namespace: robot.*
Physical robot controls, chassis kinematics, head/lift motors, autonomous docking, light cube manipulation,
OLED face expressions, backpack LEDs, IR headlight, and Cozmo hardware sensors.
Contains 26 robot tools (8 base kinematics/docking + 18 extended Cozmo-feasible actions).
"""

from typing import Dict, List

ROBOT_NAMESPACE = "robot"

# -----------------------------------------------------------------------------
# Base Physical Robot Kinematics & Docking (Active in baseline MoKa)
# -----------------------------------------------------------------------------
ROBOT_BASE_TOOLS: Dict[str, str] = {
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

# -----------------------------------------------------------------------------
# Extended Cozmo-Feasible Actions (Scaling to 100 tools)
# Hardware limits respected:
#   - Treads only: no sideways/strafing movement, no stairs (cliff sensors stop it).
#   - One forklift lift + tilting head; can only manipulate the 3 light cubes.
#   - Speaker (say_text / audio), OLED face display, camera, IR head light, 5 backpack LEDs.
#   - NO microphone and no arms/hands: nothing listens or grabs arbitrary objects.
# -----------------------------------------------------------------------------
ROBOT_EXTRA_TOOLS: Dict[str, str] = {
    # --- Voice & Display ---
    "say_text": (
        "Speaks a phrase aloud through the Cozmo robot's own speaker in its robotic voice. "
        "Use when user tells the robot to say, speak, announce, or repeat a sentence out loud."
    ),
    "set_robot_volume": (
        "Adjusts the volume of the Cozmo robot's own speaker, not the laptop. "
        "Use when user says robot talk louder, quieter, speak softer, or set Cozmo's volume."
    ),
    "show_oled_face_expression": (
        "Displays an expression on the Cozmo robot's OLED eye screen, such as happy, angry, sleepy, or surprised eyes. "
        "Use when user tells the robot to make a face, show an emotion, or change its eyes."
    ),
    # --- Lift & Head ---
    "raise_lift": (
        "Raises the Cozmo robot's forklift arm to its top position. "
        "Use when user commands the robot to lift its arm, raise the lift, or put the forklift up."
    ),
    "lower_lift": (
        "Lowers the Cozmo robot's forklift arm to the ground position. "
        "Use when user commands the robot to lower its arm, put the lift down, or drop the forklift."
    ),
    "tilt_head_up": (
        "Tilts the Cozmo robot's head and camera upward. "
        "Use when user commands the robot to look up, raise its head, or tilt the camera up."
    ),
    "tilt_head_down": (
        "Tilts the Cozmo robot's head and camera downward. "
        "Use when user commands the robot to look down, lower its head, or tilt the camera down."
    ),
    # --- Cube Manipulation ---
    "find_cube": (
        "Looks around and drives up to the nearest visible light cube without lifting it. "
        "Use when user says find your cube, go to the block, or where is your cube."
    ),
    "pick_up_cube": (
        "Drives to a Cozmo light cube and lifts it with its forklift arm. "
        "Use when user commands the robot to pick up the cube, grab the block, or lift the cube."
    ),
    "place_cube_down": (
        "Sets the cube the Cozmo robot is currently carrying down on the ground. "
        "Use when user commands the robot to put the cube down, drop the block, or release the cube."
    ),
    "stack_cubes": (
        "Picks up one Cozmo cube and stacks it on top of another cube. "
        "Use when user commands the robot to stack the cubes, build a tower, or put one block on another."
    ),
    "roll_cube": (
        "Pushes a Cozmo cube with its lift so it rolls over onto another side. "
        "Use when user commands the robot to roll the cube, flip the block, or tip over the cube."
    ),
    "pop_a_wheelie": (
        "Presses its lift against a cube to flip the Cozmo robot up onto its back treads. "
        "Use when user commands the robot to pop a wheelie, do a trick, or stand up on its back."
    ),
    # --- Lights, Camera & Senses ---
    "set_backpack_lights": (
        "Changes the color of the five LEDs on the Cozmo robot's back (backpack lights). "
        "Use when user says change your back lights, light up red, or turn your backpack lights on or off."
    ),
    "toggle_head_light": (
        "Turns the Cozmo robot's infrared headlight (night-vision LED) on or off. "
        "Use when user says turn on your headlight, night vision, or light up the front."
    ),
    "take_photo": (
        "Captures a still image from the Cozmo robot's front camera and saves it to the laptop. "
        "Use when user says take a picture with the robot, snap a photo, or what does the robot see."
    ),
    "find_face": (
        "Rotates in place scanning for human faces and greets a recognized person by name. "
        "Use when user says find my face, look for a person, who is there, or say hi to me."
    ),
    "check_robot_battery": (
        "Reports the Cozmo robot's own battery voltage and whether it is charging. "
        "Use when user asks how much battery the robot has, is Cozmo charged, or is the robot charging."
    ),
}

# Unified 26 robot tools dictionary
ROBOT_TOOLS: Dict[str, str] = {
    **ROBOT_BASE_TOOLS,
    **ROBOT_EXTRA_TOOLS,
}

# Layer 1 Tool RAG specifications for physical robot actions
ROBOT_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": ROBOT_NAMESPACE}
    for name, desc in ROBOT_TOOLS.items()
]

# Backward-compatibility alias
ROBOT_EXTRA_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": ROBOT_NAMESPACE}
    for name, desc in ROBOT_EXTRA_TOOLS.items()
]
