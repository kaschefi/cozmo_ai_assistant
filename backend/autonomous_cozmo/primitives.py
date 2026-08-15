import math
import time
import threading
from typing import List, Dict, Tuple, Optional, Any
import pycozmo

from core.hardware.connection import cozmo_manager

try:
    from core.routing.layer1.registry import reflex_registry
except Exception:
    reflex_registry = None


DEFAULT_DRIVE_SPEED = 50.0   # mm/s
DEFAULT_TURN_SPEED = 90.0    # deg/s
ROBOT_CAMERA_HEIGHT_MM = 45.0  # Camera height above desk baseline


def _is_safety_tripped() -> bool:
    """
    Checks if the active ReflexSafetyGuard instance has tripped safety.
    """
    guard = getattr(reflex_registry, "safety_guard", None) or cozmo_manager.get_safety_guard()
    if guard:
        return not guard.is_safe()
    return False


def _get_safety_reason() -> str:
    """
    Retrieves the last safety event reason from the safety guard.
    """
    guard = getattr(reflex_registry, "safety_guard", None) or cozmo_manager.get_safety_guard()
    if guard:
        return guard.last_event_reason or "Safety reflex active"
    return "Safety reflex active"


class PoseTracker:
    """
    Tracks Cozmo's estimated 2D desk-relative pose (x, y, heading) and head pitch,
    supporting dynamic coordinate updates/offsets from host vision (e.g. SLAM / REMIND)
    to mitigate track-slippage odometry drift.
    """

    def __init__(self, x: float = 0.0, y: float = 0.0, theta_deg: float = 0.0):
        self._lock = threading.Lock()
        self.x = float(x)
        self.y = float(y)
        self.theta = math.radians(theta_deg)
        self.head_pitch_rad = 0.0

        # Host dynamic drift offsets
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.offset_theta = 0.0

    def update_pose(self, x: float, y: float, theta_deg: float):
        """Directly sets raw estimated pose."""
        with self._lock:
            self.x = float(x)
            self.y = float(y)
            self.theta = math.radians(theta_deg)

    def update_relative_motion(self, dist_mm: float, turn_deg: float):
        """Updates internal pose by integrating relative forward motion and rotation."""
        with self._lock:
            self.theta += math.radians(turn_deg)
            # Normalize theta to [-pi, pi]
            self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
            self.x += dist_mm * math.cos(self.theta)
            self.y += dist_mm * math.sin(self.theta)

    def update_offset(self, dx: float, dy: float, dtheta_deg: float):
        """
        Applies dynamic coordinate corrections/offsets from external visual SLAM or host vision
        to compensate for desk odometry drift.
        """
        with self._lock:
            self.offset_x += float(dx)
            self.offset_y += float(dy)
            self.offset_theta += math.radians(dtheta_deg)

    def reset_pose(self, x: float = 0.0, y: float = 0.0, theta_deg: float = 0.0):
        """Resets pose and clears offsets."""
        with self._lock:
            self.x = float(x)
            self.y = float(y)
            self.theta = math.radians(theta_deg)
            self.offset_x = 0.0
            self.offset_y = 0.0
            self.offset_theta = 0.0

    def get_effective_pose(self) -> Tuple[float, float, float]:
        """Returns the drift-corrected effective pose (eff_x, eff_y, eff_theta_deg)."""
        with self._lock:
            eff_x = self.x + self.offset_x
            eff_y = self.y + self.offset_y
            eff_theta = math.degrees(self.theta + self.offset_theta)
            return eff_x, eff_y, eff_theta

    def get_pose(self) -> Dict[str, float]:
        """Returns complete pose state dictionary."""
        eff_x, eff_y, eff_theta_deg = self.get_effective_pose()
        with self._lock:
            return {
                "x": self.x,
                "y": self.y,
                "theta_deg": math.degrees(self.theta),
                "offset_x": self.offset_x,
                "offset_y": self.offset_y,
                "offset_theta_deg": math.degrees(self.offset_theta),
                "effective_x": eff_x,
                "effective_y": eff_y,
                "effective_theta_deg": eff_theta_deg,
                "head_pitch_deg": math.degrees(self.head_pitch_rad),
            }


# Global singleton PoseTracker for desk motion tracking
pose_tracker = PoseTracker()


# ==============================================================================
# PHASE 2 REACTIVE MOTION PRIMITIVES
# ==============================================================================

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
    :param speed_mm_s: Linear velocity in mm/s.
    :param angle_tolerance_deg: Acceptable orientation error in degrees.
    :param distance_tolerance_mm: Target arrival tolerance in mm.
    :param obstacle_avoidance: Whether artificial potential field obstacle repulsion is active.
    :param obstacles: List of static obstacle dicts [{'x': mm, 'y': mm, 'radius': mm}, ...]
    :param timeout_s: Maximum execution duration before timing out.
    """
    cli = cozmo_manager.get_robot()
    if not cli:
        # Dry-run update for offline testing
        pose_tracker.update_pose(target_x, target_y, 0.0)
        return {"status": "dry_run", "action": "drive_to", "target": (target_x, target_y)}

    if _is_safety_tripped():
        return {"status": "tripped", "error": _get_safety_reason()}

    start_time = time.time()
    obstacles = obstacles or []

    while time.time() - start_time < timeout_s:
        if _is_safety_tripped():
            cli.stop_all_motors()
            return {"status": "tripped", "error": _get_safety_reason()}

        curr_x, curr_y, curr_theta_deg = pose_tracker.get_effective_pose()
        dx = target_x - curr_x
        dy = target_y - curr_y
        dist = math.hypot(dx, dy)

        if dist <= distance_tolerance_mm:
            cli.stop_all_motors()
            return {
                "status": "success",
                "action": "drive_to",
                "target": (target_x, target_y),
                "final_pose": pose_tracker.get_pose(),
            }

        # Calculate desired heading vector (Attractive force)
        att_x = dx / dist
        att_y = dy / dist

        rep_x = 0.0
        rep_y = 0.0

        if obstacle_avoidance and obstacles:
            K_REP = 150.0  # Repulsive gain
            SAFETY_MARGIN_MM = 120.0  # Influence range beyond obstacle radius

            for obs in obstacles:
                ox = obs.get("x", 0.0)
                oy = obs.get("y", 0.0)
                radius = obs.get("radius", 30.0)
                influence_r = radius + SAFETY_MARGIN_MM

                obs_dx = curr_x - ox
                obs_dy = curr_y - oy
                obs_dist = math.hypot(obs_dx, obs_dy)

                if 0.001 < obs_dist < influence_r:
                    rep_factor = K_REP * ((1.0 / obs_dist) - (1.0 / influence_r)) / (obs_dist ** 2)
                    rep_x += (obs_dx / obs_dist) * rep_factor
                    rep_y += (obs_dy / obs_dist) * rep_factor

        net_x = att_x + rep_x
        net_y = att_y + rep_y
        desired_heading_rad = math.atan2(net_y, net_x)
        desired_heading_deg = math.degrees(desired_heading_rad)

        heading_error_deg = desired_heading_deg - curr_theta_deg
        # Normalize heading error to [-180, 180]
        heading_error_deg = (heading_error_deg + 180.0) % 360.0 - 180.0

        # Step 1: Rotate to face heading if misaligned
        if abs(heading_error_deg) > angle_tolerance_deg:
            turn_speed = DEFAULT_TURN_SPEED if heading_error_deg > 0 else -DEFAULT_TURN_SPEED
            turn_duration = min(0.3, abs(heading_error_deg) / DEFAULT_TURN_SPEED)
            cli.drive_wheels(lwheel_speed=-turn_speed, rwheel_speed=turn_speed)
            time.sleep(turn_duration)
            cli.stop_all_motors()
            actual_turn_deg = (turn_speed * turn_duration)
            pose_tracker.update_relative_motion(0.0, actual_turn_deg)
            continue

        # Step 2: Drive forward in incremental step
        step_dist = min(25.0, dist)
        step_duration = step_dist / max(10.0, speed_mm_s)

        cli.drive_wheels(lwheel_speed=speed_mm_s, rwheel_speed=speed_mm_s)
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
    wheel_speed = math.radians(speed_deg_s) * (pycozmo.robot.TRACK_WIDTH.mm / 2.0)

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
