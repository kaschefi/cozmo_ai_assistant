import time
import math
import pycozmo
from core.hardware.connection import cozmo_manager

try:
    from core.routing.layer1.registry import reflex_registry
except Exception:
    reflex_registry = None

from core.routing.layer2.tool_vector_db import tool_rag_registry

# Register Layer 2 Fallback Schemas for Physical Controls
tool_rag_registry.register_tool_schema(
    name="move_forward",
    description="Drives or rolls the Cozmo robot forward by a distance. Use when the user commands the robot to move forward, crawl forward, advance, or drive ahead."
)
tool_rag_registry.register_tool_schema(
    name="move_backward",
    description="Drives, rolls, or reverses the Cozmo robot backward. Use when the user commands the robot to move backward, back up, reverse position, or drive back."
)
tool_rag_registry.register_tool_schema(
    name="turn_left",
    description="Rotates or pivots the Cozmo robot 90 degrees to the left (counterclockwise). Use when the user commands the robot to turn left, pivot left, or look left."
)
tool_rag_registry.register_tool_schema(
    name="turn_right",
    description="Rotates or pivots the Cozmo robot 90 degrees to the right (clockwise). Use when the user commands the robot to turn right, pivot right, or look right."
)
tool_rag_registry.register_tool_schema(
    name="turn_around",
    description="Rotates the Cozmo robot 180 degrees to face backwards. Use when the user commands the robot to turn around, face the wall behind, do a 180, or flip heading."
)
tool_rag_registry.register_tool_schema(
    name="stop_movement",
    description="Emergency stops and immediately halts all robot motors and wheel movement. Use when the user commands the robot to stop, halt, freeze, stand still, or brake."
)
tool_rag_registry.register_tool_schema(
    name="arc_sweep",
    description="Scans the surrounding environment and sweeps an arc with the camera. Use when the user commands the robot to scan the area, sweep arc, survey the room, or look around."
)

# --- Head & Lift Movement Bounds ---
DEFAULT_DRIVE_SPEED = 50.0    # mm/s
DEFAULT_TURN_SPEED = 90.0     # deg/s

def _is_safety_tripped() -> bool:
    """
    Checks the active ReflexSafetyGuard instance to see if it's safe to move.
    """
    guard = (getattr(reflex_registry, "safety_guard", None) if reflex_registry else None) or cozmo_manager.get_safety_guard()
    if guard:
        return not guard.is_safe() # If not safe, safety is tripped!
    return False



def set_head_angle(angle_degrees: float, duration: float = 1.0):
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}
    if _is_safety_tripped(): return {"error": "Safety reflex active. Command dropped."}

    angle_rad = max(pycozmo.robot.MIN_HEAD_ANGLE.radians, min(pycozmo.robot.MAX_HEAD_ANGLE.radians, math.radians(angle_degrees)))
    cli.set_head_angle(angle_rad)
    if duration > 0:
        time.sleep(duration)
    return {"status": "success", "action": "set_head_angle", "angle_degrees": angle_degrees}


def move_head(speed: float, duration: float = 1.0):
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}
    if _is_safety_tripped(): return {"error": "Safety reflex active. Command dropped."}

    cli.move_head(speed)
    if duration > 0:
        time.sleep(duration)
        cli.move_head(0.0)
    return {"status": "success", "action": "move_head", "speed": speed, "duration": duration}


# -----------------------------------------------------------------------------
# Lift / Hand Control
# -----------------------------------------------------------------------------
def set_lift_height(height_mm: float, duration: float = 1.0):
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}
    if _is_safety_tripped(): return {"error": "Safety reflex active. Command dropped."}

    height_clamped = max(pycozmo.robot.MIN_LIFT_HEIGHT.mm, min(pycozmo.robot.MAX_LIFT_HEIGHT.mm, height_mm))
    cli.set_lift_height(height_clamped)
    if duration > 0:
        time.sleep(duration)
    return {"status": "success", "action": "set_lift_height", "height_mm": height_clamped}


def move_lift(speed: float, duration: float = 1.0):
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}
    if _is_safety_tripped(): return {"error": "Safety reflex active. Command dropped."}

    cli.move_lift(speed)
    if duration > 0:
        time.sleep(duration)
        cli.move_lift(0.0)
    return {"status": "success", "action": "move_lift", "speed": speed, "duration": duration}


# -----------------------------------------------------------------------------
# Drive & Turn Control (CRITICAL REFLEX PATH)
# -----------------------------------------------------------------------------
@reflex_registry.reflex(
    "move_forward",
    [
        "move forward",
        "go forward",
        "drive forward",
        "step forward",
        "drive straight ahead",
        "move forward 20 centimeters",
        "move forward a bit",
        "step forward a little bit",
        "drive ahead",
    ],
    score_threshold=0.80
)
async def move_forward(distance_mm: float = 100.0, speed_mm_s: float = DEFAULT_DRIVE_SPEED):
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}
    if _is_safety_tripped(): return {"error": "Safety reflex active. Command dropped."}

    # Instead of blocking the whole system with drive_straight, we can utilize 
    # drive_wheels loop or handle target calculations safely. 
    # For now, we guard the initiation point:
    cli.drive_straight(distance_mm=distance_mm, speed_mm_s=speed_mm_s)
    return {"status": "success", "action": "move_forward", "distance_mm": distance_mm}


@reflex_registry.reflex(
    "move_backward",
    [
        "move backward",
        "drive backward",
        "drive back",
        "move back",
        "go backward",
        "go back",
        "step back",
        "back up",
        "please back up now",
        "move back 15 cm",
    ],
    score_threshold=0.80
)
async def move_backward(distance_mm: float = 100.0, speed_mm_s: float = DEFAULT_DRIVE_SPEED):
    return await move_forward(distance_mm=-abs(distance_mm), speed_mm_s=speed_mm_s)


def turn_in_place(angle_degrees: float, speed_deg_s: float = DEFAULT_TURN_SPEED):
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}
    if _is_safety_tripped(): return {"error": "Safety reflex active. Command dropped."}

    turn_direction = 1.0 if angle_degrees > 0 else -1.0
    track_w = pycozmo.robot.TRACK_WIDTH.mm if hasattr(pycozmo.robot, "TRACK_WIDTH") else 45.0
    wheel_linear_speed = math.radians(speed_deg_s) * (track_w / 2.0)
    turn_duration = abs(angle_degrees) / max(1.0, speed_deg_s)
    l_speed = -turn_direction * wheel_linear_speed
    r_speed = turn_direction * wheel_linear_speed

    cli.drive_wheels(lwheel_speed=l_speed, rwheel_speed=r_speed)
    time.sleep(turn_duration)
    cli.stop_all_motors()
    return {"status": "success", "action": "turn_in_place", "angle_degrees": angle_degrees}


@reflex_registry.reflex(
    "turn_left",
    [
        "turn left",
        "rotate left",
        "spin left",
        "look left",
        "rotate 90 degrees to the left",
        "spin left and face the window",
        "turn to the left",
    ],
    score_threshold=0.80
)
async def turn_left(angle_degrees: float = 90.0, speed_deg_s: float = DEFAULT_TURN_SPEED):
    return turn_in_place(angle_degrees=abs(angle_degrees), speed_deg_s=speed_deg_s)


@reflex_registry.reflex(
    "turn_right",
    [
        "turn right",
        "rotate right",
        "spin right",
        "look right",
        "rotate to the right",
        "spin right 90 degrees",
        "turn to the right",
    ],
    score_threshold=0.80
)
async def turn_right(angle_degrees: float = 90.0, speed_deg_s: float = DEFAULT_TURN_SPEED):
    return turn_in_place(angle_degrees=-abs(angle_degrees), speed_deg_s=speed_deg_s)


@reflex_registry.reflex(
    "turn_around",
    [
        "turn around",
        "spin around",
        "do a 180",
        "about face",
        "do a 180 degree turn",
        "about face and turn backwards",
        "turn back",
    ],
    score_threshold=0.80
)
async def turn_around(speed_deg_s: float = DEFAULT_TURN_SPEED):
    return turn_in_place(angle_degrees=180.0, speed_deg_s=speed_deg_s)


def drive_wheels(left_speed: float, right_speed: float, duration: float = 0.0):
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}
    if _is_safety_tripped(): return {"error": "Safety reflex active. Command dropped."}

    cli.drive_wheels(lwheel_speed=left_speed, rwheel_speed=right_speed)
    if duration > 0:
        time.sleep(duration)
        cli.stop_all_motors()
    return {"status": "success", "action": "drive_wheels", "left": left_speed, "right": right_speed}


# -----------------------------------------------------------------------------
# Emergency Stop (MUST ALWAYS WORK - BYPASSES REFLEX CHECKS)
# -----------------------------------------------------------------------------
@reflex_registry.reflex(
    "stop_movement",
    [
        "stop",
        "halt",
        "freeze",
        "stop moving",
        "break",
        "stop moving immediately",
        "halt all motors right now",
        "freeze and stop",
        "emergency stop",
    ],
    score_threshold=0.80
)
async def stop_movement():
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}

    # This bypasses the safety trip check so we can always explicitly stop everything
    cli.stop_all_motors()
    return {"status": "success", "action": "stop_movement"}


# -----------------------------------------------------------------------------
# Phase 2 Reactive Motion Primitives Integration
# -----------------------------------------------------------------------------
from autonomous_cozmo.motion import (
    PoseTracker,
    pose_tracker,
    drive_to as _drive_to,
    look_at as _look_at,
    arc_sweep as _arc_sweep,
)

def drive_to(target_x: float, target_y: float, speed_mm_s: float = DEFAULT_DRIVE_SPEED, obstacle_avoidance: bool = True, obstacles=None):
    return _drive_to(target_x=target_x, target_y=target_y, speed_mm_s=speed_mm_s, obstacle_avoidance=obstacle_avoidance, obstacles=obstacles)

def look_at(target_x: float, target_y: float, target_z: float = 0.0, speed_deg_s: float = DEFAULT_TURN_SPEED):
    return _look_at(target_x=target_x, target_y=target_y, target_z=target_z, speed_deg_s=speed_deg_s)

def _register_reflex(name, utterances, score_threshold=0.80, speech=""):
    if reflex_registry:
        return reflex_registry.reflex(name, utterances, score_threshold=score_threshold, speech=speech)
    def dummy_decorator(func):
        return func
    return dummy_decorator

@_register_reflex(
    "arc_sweep",
    [
        "scan area",
        "sweep arc",
        "look around",
        "observe surroundings",
        "scan the surrounding area",
        "sweep arc and observe the room",
        "look around your surroundings",
        "look around the area",
    ],
    score_threshold=0.80
)
async def arc_sweep(angle_range_deg: float = 60.0, head_tilt_deg: float = 10.0):
    return _arc_sweep(angle_range_deg=angle_range_deg, head_tilt_deg=head_tilt_deg)