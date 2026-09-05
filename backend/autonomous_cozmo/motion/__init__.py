"""
Autonomous Cozmo Motion Package (Phase 2 & Phase 5 - Reactive Motion & Bidirectional A* Docking)
Provides closed-loop kinematic building blocks, odometry drift tracking,
potential field obstacle avoidance, and Two-Way A* path planning with 5cm clearance.
"""

from .pose_tracker import PoseTracker, pose_tracker
from .potential_fields import (
    compute_attractive_force,
    compute_obstacle_repulsion,
    compute_apf_heading,
)
from .bidirectional_astar import (
    BidirectionalAStarPlanner,
    bidirectional_astar_planner,
    PathPlanningResult,
    BlockObstacle,
    DEFAULT_BLOCK_SIZE_MM,
    DEFAULT_BLOCK_RADIUS_MM,
    DEFAULT_SAFETY_CLEARANCE_MM,
    DEFAULT_ROBOT_RADIUS_MM,
)
from .primitives import (
    drive_to,
    follow_path,
    look_at,
    arc_sweep,
    _is_safety_tripped,
    _get_safety_reason,
    DEFAULT_DRIVE_SPEED,
    DEFAULT_TURN_SPEED,
    ROBOT_CAMERA_HEIGHT_MM,
    TRACK_WIDTH_MM,
)

from .visual_servoing import (
    VisualServoingDockingController,
    visual_servoing_controller,
)

__all__ = [
    "PoseTracker",
    "pose_tracker",
    "compute_attractive_force",
    "compute_obstacle_repulsion",
    "compute_apf_heading",
    "BidirectionalAStarPlanner",
    "bidirectional_astar_planner",
    "PathPlanningResult",
    "BlockObstacle",
    "DEFAULT_BLOCK_SIZE_MM",
    "DEFAULT_BLOCK_RADIUS_MM",
    "DEFAULT_SAFETY_CLEARANCE_MM",
    "DEFAULT_ROBOT_RADIUS_MM",
    "drive_to",
    "follow_path",
    "look_at",
    "arc_sweep",
    "_is_safety_tripped",
    "_get_safety_reason",
    "DEFAULT_DRIVE_SPEED",
    "DEFAULT_TURN_SPEED",
    "ROBOT_CAMERA_HEIGHT_MM",
    "TRACK_WIDTH_MM",
    "VisualServoingDockingController",
    "visual_servoing_controller",
]

