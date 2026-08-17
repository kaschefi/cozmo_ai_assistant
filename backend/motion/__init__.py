"""
Motion Package (Phase 2 - Reactive Motion Primitives)
Provides closed-loop kinematic building blocks, odometry drift tracking,
and artificial potential field obstacle avoidance.
"""

from .pose_tracker import PoseTracker, pose_tracker
from .potential_fields import (
    compute_attractive_force,
    compute_obstacle_repulsion,
    compute_apf_heading,
)
from .primitives import (
    drive_to,
    look_at,
    arc_sweep,
    _is_safety_tripped,
    _get_safety_reason,
    DEFAULT_DRIVE_SPEED,
    DEFAULT_TURN_SPEED,
    ROBOT_CAMERA_HEIGHT_MM,
    TRACK_WIDTH_MM,
)

__all__ = [
    "PoseTracker",
    "pose_tracker",
    "compute_attractive_force",
    "compute_obstacle_repulsion",
    "compute_apf_heading",
    "drive_to",
    "look_at",
    "arc_sweep",
    "_is_safety_tripped",
    "_get_safety_reason",
    "DEFAULT_DRIVE_SPEED",
    "DEFAULT_TURN_SPEED",
    "ROBOT_CAMERA_HEIGHT_MM",
    "TRACK_WIDTH_MM",
]
