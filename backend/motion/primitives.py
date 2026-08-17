import math
import time
from typing import List, Dict, Tuple, Optional, Any
import pycozmo

from core.hardware.connection import cozmo_manager
from .pose_tracker import pose_tracker
from .potential_fields import compute_apf_heading

try:
    from core.routing.layer1.registry import reflex_registry
except Exception:
    reflex_registry = None


DEFAULT_DRIVE_SPEED = 50.0      # mm/s
DEFAULT_TURN_SPEED = 90.0       # deg/s
ROBOT_CAMERA_HEIGHT_MM = 45.0   # Camera height above desk baseline (mm)
TRACK_WIDTH_MM = pycozmo.robot.TRACK_WIDTH.mm if hasattr(pycozmo.robot, "TRACK_WIDTH") else 45.0


def _is_safety_tripped() -> bool:
    """
    Checks if the active ReflexSafetyGuard instance has tripped safety.
    """
    guard = (getattr(reflex_registry, "safety_guard", None) if reflex_registry else None) or cozmo_manager.get_safety_guard()
    if guard:
        return not guard.is_safe()
    return False


def _get_safety_reason() -> str:
    """
    Retrieves the last safety event reason from the safety guard.
    """
    guard = (getattr(reflex_registry, "safety_guard", None) if reflex_registry else None) or cozmo_manager.get_safety_guard()
    if guard:
        return guard.last_event_reason or "Safety reflex active"
    return "Safety reflex active"


def drive_to(
    target_x: float,
    target_y: float,
    speed_mm_s: float = DEFAULT_DRIVE_SPEED,
    angle_tolerance_deg: float = 5.0,
    distance_tolerance_mm: float = 15.0,
    obstacle_avoidance: bool = True,
    obstacles: Optional[List[Dict[str, float]]] = None,
    timeout_s: float = 15.0,
) -> Dict[str, Any]:
    """
    Moves Cozmo toward a targeted point on the desk-relative coordinate frame (x, y).
    Integrates safety checks on every step loop and optional vector-field obstacle avoidance.

    :param target_x: Desk target X coordinate in mm.
    :param target_y: Desk target Y coordinate in mm.
    :param speed_mm_s: Maximum linear velocity in mm/s.
    :param angle_tolerance_deg: Acceptable orientation error in degrees.
    :param distance_tolerance_mm: Target arrival tolerance in mm.
    :param obstacle_avoidance: Whether artificial potential field obstacle repulsion is active.
    :param obstacles: List of static obstacle dicts [{'x': mm, 'y': mm, 'radius': mm}, ...]
    :param timeout_s: Maximum execution duration before timing out.
    """
    cli = cozmo_manager.get_robot()
    if not cli:
        # Dry-run update for offline simulation / testing
        pose_tracker.update_pose(target_x, target_y, 0.0)
        return {"status": "dry_run", "action": "drive_to", "target": (target_x, target_y)}

    if _is_safety_tripped():
        return {"status": "tripped", "error": _get_safety_reason()}

    start_time = time.time()
    active_obstacles = obstacles if obstacle_avoidance else None

    while time.time() - start_time < timeout_s:
        if _is_safety_tripped():
            cli.stop_all_motors()
            return {"status": "tripped", "error": _get_safety_reason()}

        curr_x, curr_y, curr_theta_deg = pose_tracker.get_effective_pose()

        # Compute desired steering heading & distance via Artificial Potential Field
        desired_heading_deg, dist = compute_apf_heading(
            curr_x=curr_x,
            curr_y=curr_y,
            target_x=target_x,
            target_y=target_y,
            obstacles=active_obstacles,
        )

        if dist <= distance_tolerance_mm:
            cli.stop_all_motors()
            return {
                "status": "success",
                "action": "drive_to",
                "target": (target_x, target_y),
                "final_pose": pose_tracker.get_pose(),
            }

        heading_error_deg = desired_heading_deg - curr_theta_deg
        # Normalize heading error to [-180, 180]
        heading_error_deg = (heading_error_deg + 180.0) % 360.0 - 180.0

        # Step 1: Rotate to align with desired vector field heading
        if abs(heading_error_deg) > angle_tolerance_deg:
            turn_direction = 1.0 if heading_error_deg > 0 else -1.0
            turn_rate_deg_s = min(DEFAULT_TURN_SPEED, max(30.0, abs(heading_error_deg) * 2.0))
            
            # Convert angular velocity (deg/s) to differential wheel linear speed (mm/s)
            wheel_linear_speed = math.radians(turn_rate_deg_s) * (TRACK_WIDTH_MM / 2.0)
            turn_duration = min(0.35, abs(heading_error_deg) / turn_rate_deg_s)

            # Left turn (+deg) -> Left wheel backward, Right wheel forward
            l_speed = -turn_direction * wheel_linear_speed
            r_speed = turn_direction * wheel_linear_speed

            cli.drive_wheels(lwheel_speed=l_speed, rwheel_speed=r_speed)
            time.sleep(turn_duration)
            cli.stop_all_motors()

            actual_turn_deg = turn_direction * turn_rate_deg_s * turn_duration
            pose_tracker.update_relative_motion(0.0, actual_turn_deg)
            continue

        # Step 2: Drive forward in incremental step with smooth deceleration near goal
        effective_speed = speed_mm_s
        if dist < 35.0:
            effective_speed = max(15.0, speed_mm_s * (dist / 35.0))

        step_dist = min(25.0, dist)
        step_duration = step_dist / max(10.0, effective_speed)

        cli.drive_wheels(lwheel_speed=effective_speed, rwheel_speed=effective_speed)
        time.sleep(step_duration)
        cli.stop_all_motors()

        pose_tracker.update_relative_motion(step_dist, 0.0)

    cli.stop_all_motors()
    return {"status": "timeout", "action": "drive_to", "target": (target_x, target_y)}


def look_at(
    target_x: float,
    target_y: float,
    target_z: float = 0.0,
    speed_deg_s: float = DEFAULT_TURN_SPEED,
) -> Dict[str, Any]:
    """
    Rotates the chassis and tilts the camera head to orient directly toward a 3D desk coordinate (x, y, z).

    :param target_x: Desk target X coordinate in mm.
    :param target_y: Desk target Y coordinate in mm.
    :param target_z: Height Z above desk plane in mm.
    :param speed_deg_s: Rotation speed deg/s.
    """
    cli = cozmo_manager.get_robot()
    if not cli:
        pose_tracker.head_pitch_rad = math.atan2(target_z - ROBOT_CAMERA_HEIGHT_MM, 100.0)
        return {"status": "dry_run", "action": "look_at", "target": (target_x, target_y, target_z)}

    if _is_safety_tripped():
        return {"status": "tripped", "error": _get_safety_reason()}

    curr_x, curr_y, curr_theta_deg = pose_tracker.get_effective_pose()
    dx = target_x - curr_x
    dy = target_y - curr_y
    dist_xy = math.hypot(dx, dy)

    # Calculate horizontal target yaw heading
    target_yaw_rad = math.atan2(dy, dx)
    target_yaw_deg = math.degrees(target_yaw_rad)

    heading_error_deg = target_yaw_deg - curr_theta_deg
    heading_error_deg = (heading_error_deg + 180.0) % 360.0 - 180.0

    # Calculate vertical target camera pitch angle
    dz = target_z - ROBOT_CAMERA_HEIGHT_MM
    target_pitch_rad = math.atan2(dz, max(10.0, dist_xy))

    # Clamp head angle to physical PyCozmo bounds
    clamped_pitch_rad = max(
        pycozmo.robot.MIN_HEAD_ANGLE,
        min(pycozmo.robot.MAX_HEAD_ANGLE, target_pitch_rad)
    )

    # Execute head tilt
    try:
        cli.set_head_angle(clamped_pitch_rad)
        pose_tracker.head_pitch_rad = clamped_pitch_rad
    except Exception as e:
        print(f"[Primitives] Failed to set head angle in look_at: {e}")

    # Execute chassis rotation if needed
    if abs(heading_error_deg) > 3.0:
        turn_rad = math.radians(heading_error_deg)
        speed_rad_s = math.radians(speed_deg_s)
        try:
            cli.turn_in_place(angle_rad=turn_rad, speed_rad_s=speed_rad_s)
            pose_tracker.update_relative_motion(0.0, heading_error_deg)
        except Exception as e:
            print(f"[Primitives] Failed to turn in look_at: {e}")

    return {
        "status": "success",
        "action": "look_at",
        "target": (target_x, target_y, target_z),
        "heading_deg": target_yaw_deg,
        "pitch_deg": math.degrees(clamped_pitch_rad),
    }


def arc_sweep(
    angle_range_deg: float = 60.0,
    head_tilt_deg: float = 10.0,
    speed_deg_s: float = 30.0,
    steps: int = 4,
) -> Dict[str, Any]:
    """
    Executes a slow, smooth scanning motion (sweeping chassis left and right while tilting head)
    used for idle observing animations.

    :param angle_range_deg: Total horizontal scan arc in degrees.
    :param head_tilt_deg: Pitch excursion angle in degrees.
    :param speed_deg_s: Turn speed during sweep.
    :param steps: Number of incremental sweep steps per direction.
    """
    cli = cozmo_manager.get_robot()
    half_arc = angle_range_deg / 2.0

    if not cli:
        return {"status": "dry_run", "action": "arc_sweep", "arc_deg": angle_range_deg}

    if _is_safety_tripped():
        return {"status": "tripped", "error": _get_safety_reason()}

    step_deg = half_arc / float(steps)
    step_duration = step_deg / speed_deg_s
    wheel_speed = math.radians(speed_deg_s) * (TRACK_WIDTH_MM / 2.0)

    # Step 1: Sweep Left while raising head slightly
    base_pitch = pose_tracker.head_pitch_rad
    for i in range(steps):
        if _is_safety_tripped():
            cli.stop_all_motors()
            return {"status": "tripped", "error": _get_safety_reason()}

        cli.drive_wheels(lwheel_speed=-wheel_speed, rwheel_speed=wheel_speed)
        time.sleep(step_duration)
        cli.stop_all_motors()

        pose_tracker.update_relative_motion(0.0, step_deg)

        # Modulate head tilt
        current_tilt = base_pitch + math.radians((i + 1) / steps * head_tilt_deg)
        clamped_tilt = max(pycozmo.robot.MIN_HEAD_ANGLE, min(pycozmo.robot.MAX_HEAD_ANGLE, current_tilt))
        cli.set_head_angle(clamped_tilt)
        pose_tracker.head_pitch_rad = clamped_tilt

    # Step 2: Sweep Right back across the arc while lowering head
    for i in range(steps * 2):
        if _is_safety_tripped():
            cli.stop_all_motors()
            return {"status": "tripped", "error": _get_safety_reason()}

        cli.drive_wheels(lwheel_speed=wheel_speed, rwheel_speed=-wheel_speed)
        time.sleep(step_duration)
        cli.stop_all_motors()

        pose_tracker.update_relative_motion(0.0, -step_deg)

        current_tilt = base_pitch + math.radians((1.0 - (i / (steps * 2))) * head_tilt_deg)
        clamped_tilt = max(pycozmo.robot.MIN_HEAD_ANGLE, min(pycozmo.robot.MAX_HEAD_ANGLE, current_tilt))
        cli.set_head_angle(clamped_tilt)
        pose_tracker.head_pitch_rad = clamped_tilt

    # Step 3: Return chassis to center heading
    for _ in range(steps):
        if _is_safety_tripped():
            cli.stop_all_motors()
            return {"status": "tripped", "error": _get_safety_reason()}

        cli.drive_wheels(lwheel_speed=-wheel_speed, rwheel_speed=wheel_speed)
        time.sleep(step_duration)
        cli.stop_all_motors()

        pose_tracker.update_relative_motion(0.0, step_deg)

    cli.set_head_angle(base_pitch)
    pose_tracker.head_pitch_rad = base_pitch

    return {"status": "success", "action": "arc_sweep", "arc_deg": angle_range_deg}
