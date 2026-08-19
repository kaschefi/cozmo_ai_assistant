import time
from typing import List, Dict, Tuple, Optional, Any
from ..tree import Node, NodeStatus, Blackboard
from ...motion import drive_to, arc_sweep, pose_tracker
from ...vision.remind_engine import remind_engine


class SelectDynamicWanderTargetNode(Node):
    """
    Action Node (Phase 4 Dynamic REMIND Target Selection):
    Replaces static lists with dynamic visual memory indexing:
    1. Priority 1: Novel / unvisited detected objects (remind_engine.get_novel_objects())
    2. Priority 2: Least recently attended objects (remind_engine.get_least_recently_attended())
    3. Priority 3: Exploratory sector waypoints if visual memory is empty.
    """
    DEFAULT_FALLBACK_EXPLORE_WAYPOINTS: List[Dict[str, Any]] = [
        {"name": "Sector 1 (Center Desk)", "x": 120.0, "y": 0.0, "scan": True},
        {"name": "Sector 2 (Front Left)", "x": 120.0, "y": 60.0, "scan": True},
        {"name": "Sector 3 (Back Left)", "x": 0.0, "y": 60.0, "scan": True},
        {"name": "Sector 4 (Origin Sector)", "x": 0.0, "y": 0.0, "scan": False},
    ]

    def __init__(
        self,
        name: str = "SelectDynamicWanderTarget",
        fallback_waypoints: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(name)
        self.fallback_waypoints = fallback_waypoints or self.DEFAULT_FALLBACK_EXPLORE_WAYPOINTS
        self.fallback_idx = 0

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        # 1. Check for Novel Objects
        novel_objects = remind_engine.get_novel_objects()
        if novel_objects:
            target_obj = novel_objects[0]
            print(f"[BehaviorTree/REMIND] Found novel unvisited target '{target_obj.name}' at ({target_obj.estimated_x:.1f}, {target_obj.estimated_y:.1f})")
            blackboard.set("target_id", target_obj.id)
            blackboard.set("target_x", target_obj.estimated_x)
            blackboard.set("target_y", target_obj.estimated_y)
            blackboard.set("target_name", f"[NOVEL] {target_obj.name}")
            blackboard.set("should_scan", True)
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        # 2. Check for Least Recently Attended Objects
        attended_objects = remind_engine.get_least_recently_attended()
        if attended_objects:
            target_obj = attended_objects[0]
            elapsed_s = time.time() - target_obj.last_attended_time
            print(f"[BehaviorTree/REMIND] Cycling to least recently attended '{target_obj.name}' (elapsed: {elapsed_s:.1f}s) at ({target_obj.estimated_x:.1f}, {target_obj.estimated_y:.1f})")
            blackboard.set("target_id", target_obj.id)
            blackboard.set("target_x", target_obj.estimated_x)
            blackboard.set("target_y", target_obj.estimated_y)
            blackboard.set("target_name", f"[REVISIT] {target_obj.name}")
            blackboard.set("should_scan", True)
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        # 3. Fallback to exploratory sector waypoint
        if not self.fallback_waypoints:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

        fallback_target = self.fallback_waypoints[self.fallback_idx]
        self.fallback_idx = (self.fallback_idx + 1) % len(self.fallback_waypoints)

        blackboard.set("target_id", None)
        blackboard.set("target_x", float(fallback_target["x"]))
        blackboard.set("target_y", float(fallback_target["y"]))
        blackboard.set("target_name", fallback_target.get("name", f"Sector_{self.fallback_idx}"))
        blackboard.set("should_scan", fallback_target.get("scan", True))

        self.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS


# Backward-compatibility alias for Phase 3 tests
SelectNextWanderTargetNode = SelectDynamicWanderTargetNode


class ExecuteDriveToTargetNode(Node):
    """
    Action Node:
    Retrieves the current target coordinates from the blackboard and executes drive_to().
    If a cliff/bump reflex trips, logs the event and fails gracefully so the tree can pick another target.
    """
    def __init__(self, name: str = "ExecuteDriveToTarget", speed_mm_s: float = 45.0):
        super().__init__(name)
        self.speed_mm_s = speed_mm_s
        self._is_running = False

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        target_x = blackboard.get("target_x")
        target_y = blackboard.get("target_y")

        if target_x is None or target_y is None:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

        target_name = blackboard.get("target_name", "Target")
        print(f"[BehaviorTree/Wander] Driving toward {target_name} ({target_x:.1f}, {target_y:.1f})...")
        self._is_running = True

        res = drive_to(
            target_x=target_x,
            target_y=target_y,
            speed_mm_s=self.speed_mm_s,
            obstacle_avoidance=True,
            distance_tolerance_mm=10.0,
            timeout_s=12.0,
        )

        self._is_running = False

        if res.get("status") in ("success", "dry_run"):
            curr_pose = pose_tracker.get_pose()
            print(f"[BehaviorTree/Wander] Reached {target_name}! Pose: ({curr_pose['effective_x']:.1f}, {curr_pose['effective_y']:.1f}, {curr_pose['effective_theta_deg']:.1f}°)")
            blackboard.set("last_action", f"reached_{target_name}")
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        elif res.get("status") == "tripped":
            reason = res.get("error", "Safety Reflex")
            print(f"[BehaviorTree/Wander] Safety reflex intervened: {reason}. Bypassing waypoint.")
            blackboard.set("last_safety_trip", reason)
            # Fail gracefully so sequence resets and chooses next waypoint
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

        else:
            print(f"[BehaviorTree/Wander] Navigation timed out or failed: {res.get('status')}")
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

    def cancel(self):
        super().cancel()
        self._is_running = False


class ExecuteIdleObservationNode(Node):
    """
    Action Node:
    Executes a reactive curiosity arc sweep and brief dwell pause at the reached waypoint.
    Updates REMIND visual memory attended timestamp.
    """
    def __init__(
        self,
        name: str = "ExecuteIdleObservation",
        angle_range_deg: float = 35.0,
        head_tilt_deg: float = 12.0,
        dwell_time_s: float = 0.5,
    ):
        super().__init__(name)
        self.angle_range_deg = angle_range_deg
        self.head_tilt_deg = head_tilt_deg
        self.dwell_time_s = dwell_time_s

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if not blackboard.get("should_scan", True):
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        print(f"[BehaviorTree/Wander] Executing idle arc sweep & observation...")
        res = arc_sweep(
            angle_range_deg=self.angle_range_deg,
            head_tilt_deg=self.head_tilt_deg,
            speed_deg_s=30.0,
        )

        # Update REMIND attended timestamp
        target_id = blackboard.get("target_id")
        if target_id:
            remind_engine.mark_attended(target_id)
            print(f"[BehaviorTree/REMIND] Marked object '{target_id}' as attended.")

        if res.get("status") in ("success", "dry_run"):
            if self.dwell_time_s > 0:
                time.sleep(self.dwell_time_s)
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        else:
            print(f"[BehaviorTree/Wander] Arc sweep interrupted: {res.get('error')}")
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
