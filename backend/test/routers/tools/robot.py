# backend/test/routers/tools/robot.py
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
        "Commands the physical Cozmo robot to navigate onto its charging base station cradle to recharge. "
        "Use when user tells the robot to dock, head back to charging cradle, battery is low dock yourself, or return to home base and charge up. "
        "Controls physical robot docking on charging station, not computer or laptop sleep."
    ),
    "arc_sweep": (
        "Executes a horizontal panoramic scanning sweep of the surrounding room with camera and tracks. "
        "Use when user commands the robot to perform a visual scan of the surrounding area, pan camera across the room and look around, or execute a sweeping survey arc. "
        "For horizontal room surveys, not vertical camera tilt up or down."
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
        "Adjusts the Cozmo robot's own internal hardware speaker audio volume. "
        "Use when user says make Cozmo speak quieter, turn up Cozmo robot speaker volume, speak softer, or adjust robot audio level."
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
        "Tilts the Cozmo robot head and camera vertically upwards towards the ceiling or user's face. "
        "Use when user commands the robot to tilt head and camera up towards ceiling, look upwards with camera, or angle robot head up to see my face."
    ),
    "tilt_head_down": (
        "Tilts the Cozmo robot head and camera vertically downwards towards the desk or tracks. "
        "Use when user commands the robot to tilt head down to look at the desk, look downward with front camera, or angle camera down towards tracks."
    ),
    # --- Cube Manipulation ---
    "find_cube": (
        "Navigates towards the nearest visible light cube block without lifting it. "
        "Use when user says find your cube, go to the block, locate the cube, or where is your cube."
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
        "Captures a still photographic image from the Cozmo robot's physical onboard front camera and saves it. "
        "Use when user says take a picture with robot camera, snap a photo of what Cozmo sees, or capture an image from front camera (distinct from PC screenshot)."
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
