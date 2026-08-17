"""
Autonomous Cozmo Subproject Package
Contains high-level idle behaviors, behavior trees, spatial memory, and reactive motion primitives.
"""

from .motion import (
    PoseTracker,
    pose_tracker,
    drive_to,
    look_at,
    arc_sweep,
    compute_attractive_force,
    compute_obstacle_repulsion,
    compute_apf_heading,
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
    "drive_to",
    "look_at",
    "arc_sweep",
    "compute_attractive_force",
    "compute_obstacle_repulsion",
    "compute_apf_heading",
    "_is_safety_tripped",
    "_get_safety_reason",
    "DEFAULT_DRIVE_SPEED",
    "DEFAULT_TURN_SPEED",
    "ROBOT_CAMERA_HEIGHT_MM",
    "TRACK_WIDTH_MM",
]
