import time
from typing import List, Dict, Tuple, Optional, Any
from ..tree import Node, NodeStatus, Blackboard
from ...motion import drive_to, arc_sweep, pose_tracker


class SelectNextWanderTargetNode(Node):
    """
    Action Node (Phase 3 Fixed Target Wander Selection):
    Cycles sequentially through a static list of safe desk waypoints,
    storing the next active target coordinate on the blackboard.
    """
    DEFAULT_WANDER_WAYPOINTS: List[Dict[str, Any]] = [
        {"name": "Desk Center", "x": 150.0, "y": 0.0, "scan": True},
        {"name": "Front Left", "x": 150.0, "y": 80.0, "scan": True},
        {"name": "Back Left", "x": 0.0, "y": 80.0, "scan": True},
        {"name": "Back Right", "x": -80.0, "y": 0.0, "scan": True},
    ]

    def __init__(
        self,
        name: str = "SelectNextWanderTarget",
        waypoints: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(name)
        self.waypoints = waypoints or self.DEFAULT_WANDER_WAYPOINTS
        self.current_idx = 0

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if not self.waypoints:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

        target = self.waypoints[self.current_idx]
        blackboard.set("current_target", target)
        blackboard.set("target_x", float(target["x"]))
        blackboard.set("target_y", float(target["y"]))
        blackboard.set("target_name", target.get("name", f"Target_{self.current_idx}"))
        blackboard.set("should_scan", target.get("scan", True))

        # Advance index circularly for next time
        self.current_idx = (self.current_idx + 1) % len(self.waypoints)

        self.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS


class ExecuteDriveToTargetNode(Node):
    """
    Action Node:
    Retrieves the current target coordinates from the blackboard and executes drive_to().
    If a cliff/bump reflex trips, logs the event and fails gracefully so the tree can pick another target.
    """
    def __init__(self, name: str = "ExecuteDriveToTarget", speed_mm_s: float = 50.0):
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
    """
    def __init__(
        self,
        name: str = "ExecuteIdleObservation",
        angle_range_deg: float = 35.0,
        head_tilt_deg: float = 12.0,
        dwell_time_s: float = 1.0,
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

        if res.get("status") in ("success", "dry_run"):
            if self.dwell_time_s > 0:
                time.sleep(self.dwell_time_s)
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        else:
            print(f"[BehaviorTree/Wander] Arc sweep interrupted: {res.get('error')}")
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
