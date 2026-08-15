import time
import math
import pycozmo
from core.hardware.connection import cozmo_manager

try:
    from core.routing.layer1.registry import reflex_registry
except Exception:
    reflex_registry = None

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

    angle_rad = max(pycozmo.robot.MIN_HEAD_ANGLE, min(pycozmo.robot.MAX_HEAD_ANGLE, math.radians(angle_degrees)))
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
@reflex_registry.reflex("move_forward", ["move forward", "go forward", "drive forward", "step forward"])
async def move_forward(distance_mm: float = 100.0, speed_mm_s: float = DEFAULT_DRIVE_SPEED):
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}
    if _is_safety_tripped(): return {"error": "Safety reflex active. Command dropped."}

    # Instead of blocking the whole system with drive_straight, we can utilize 
    # drive_wheels loop or handle target calculations safely. 
    # For now, we guard the initiation point:
    cli.drive_straight(distance_mm=distance_mm, speed_mm_s=speed_mm_s)
    return {"status": "success", "action": "move_forward", "distance_mm": distance_mm}


async def move_backward(distance_mm: float = 100.0, speed_mm_s: float = DEFAULT_DRIVE_SPEED):
    return await move_forward(distance_mm=-abs(distance_mm), speed_mm_s=speed_mm_s)


def turn_in_place(angle_degrees: float, speed_deg_s: float = DEFAULT_TURN_SPEED):
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}
    if _is_safety_tripped(): return {"error": "Safety reflex active. Command dropped."}

    angle_rad = math.radians(angle_degrees)
    speed_rad_s = math.radians(speed_deg_s)
    cli.turn_in_place(angle_rad=angle_rad, speed_rad_s=speed_rad_s)
    return {"status": "success", "action": "turn_in_place", "angle_degrees": angle_degrees}


@reflex_registry.reflex("turn_left", ["turn left", "rotate left", "spin left", "look left"])
async def turn_left(angle_degrees: float = 90.0, speed_deg_s: float = DEFAULT_TURN_SPEED):
    return turn_in_place(angle_degrees=abs(angle_degrees), speed_deg_s=speed_deg_s)


@reflex_registry.reflex("turn_right", ["turn right", "rotate right", "spin right", "look right"])
async def turn_right(angle_degrees: float = 90.0, speed_deg_s: float = DEFAULT_TURN_SPEED):
    return turn_in_place(angle_degrees=-abs(angle_degrees), speed_deg_s=speed_deg_s)


@reflex_registry.reflex("turn_around", ["turn around", "spin around", "do a 180", "about face"])
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
@reflex_registry.reflex("stop_movement", ["stop", "halt", "freeze", "stop moving", "break"])
async def stop_movement():
    cli = cozmo_manager.get_robot()
    if not cli: return {"error": "Robot not connected"}

    # This bypasses the safety trip check so we can always explicitly stop everything
    cli.stop_all_motors()
    return {"status": "success", "action": "stop_movement"}


# -----------------------------------------------------------------------------
# Phase 2 Reactive Motion Primitives Integration
# -----------------------------------------------------------------------------
from autonomous_cozmo.primitives import (
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

def _register_reflex(name, utterances, score_threshold=0.85, speech=""):
    if reflex_registry:
        return reflex_registry.reflex(name, utterances, score_threshold=score_threshold, speech=speech)
    def dummy_decorator(func):
        return func
    return dummy_decorator

@_register_reflex("arc_sweep", ["scan area", "sweep arc", "look around", "observe surroundings"])
async def arc_sweep(angle_range_deg: float = 60.0, head_tilt_deg: float = 10.0):
    return _arc_sweep(angle_range_deg=angle_range_deg, head_tilt_deg=head_tilt_deg)