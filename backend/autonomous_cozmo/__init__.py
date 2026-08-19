"""
Autonomous Cozmo Subproject Package
Contains high-level idle behaviors, behavior trees, spatial memory, REMIND vision, and reactive motion primitives.
"""

# Kinematic Motion Primitives (Phases 1 & 2)
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

# Behavior Tree & Idle Decision Engine (Phase 3)
from .behavior import (
    Node,
    NodeStatus,
    Selector,
    Sequence,
    ActionNode,
    ConditionNode,
    Blackboard,
    BatteryMonitor,
    battery_monitor,
    IdleBehaviorEngine,
    idle_engine,
    IsBatteryLowCondition,
    ExecuteDockingAction,
    CheckVisibleAnchorCondition,
    ExecuteSLAMOffsetCorrectionAction,
    SelectDynamicWanderTargetNode,
    SelectNextWanderTargetNode,
    ExecuteDriveToTargetNode,
    ExecuteIdleObservationNode,
)

# REMIND Visual Memory & Landmark SLAM (Phase 4)
from .vision import (
    DINOExtractor,
    VisualMemoryItem,
    TemporalDebouncer,
    REMINDMemoryEngine,
    remind_engine,
    LandmarkSLAM,
    landmark_slam,
)

__all__ = [
    # Motion
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
    # Behavior
    "Node",
    "NodeStatus",
    "Selector",
    "Sequence",
    "ActionNode",
    "ConditionNode",
    "Blackboard",
    "BatteryMonitor",
    "battery_monitor",
    "IdleBehaviorEngine",
    "idle_engine",
    "IsBatteryLowCondition",
    "ExecuteDockingAction",
    "CheckVisibleAnchorCondition",
    "ExecuteSLAMOffsetCorrectionAction",
    "SelectDynamicWanderTargetNode",
    "SelectNextWanderTargetNode",
    "ExecuteDriveToTargetNode",
    "ExecuteIdleObservationNode",
    # Vision
    "DINOExtractor",
    "VisualMemoryItem",
    "TemporalDebouncer",
    "REMINDMemoryEngine",
    "remind_engine",
    "LandmarkSLAM",
    "landmark_slam",
]
