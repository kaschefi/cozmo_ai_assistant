import time
from typing import Optional, Tuple
from ..tree import Node, NodeStatus, Blackboard
from ..battery_monitor import battery_monitor
from ...motion import drive_to, pose_tracker


class IsBatteryLowCondition(Node):
    """
    Condition Node:
    Returns SUCCESS if filtered battery telemetry indicates low/critical voltage,
    triggering the top-priority Docking branch of the Behavior Tree.
    Returns FAILURE if battery level is healthy.
    """
    def __init__(self, name: str = "IsBatteryLow?"):
        super().__init__(name)

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        is_low = battery_monitor.is_battery_low()
        blackboard.set("battery_status", battery_monitor.get_telemetry_status())

        if is_low:
            self.status = NodeStatus.SUCCESS
        else:
            self.status = NodeStatus.FAILURE
        return self.status


class ExecuteDockingAction(Node):
    """
    Action Node (Phase 3 Fixed Target Docking):
    Drives Cozmo directly toward the hardcoded charging dock position.
    Once arrived, marks robot as docked on the blackboard.
    """
    DEFAULT_DOCK_COORDINATES: Tuple[float, float] = (0.0, 0.0)

    def __init__(
        self,
        name: str = "ExecuteDockingAction",
        dock_x: float = 0.0,
        dock_y: float = 0.0,
    ):
        super().__init__(name)
        self.dock_x = float(dock_x)
        self.dock_y = float(dock_y)
        self._is_active = False

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if blackboard.get("is_docked", False):
            # Already at dock
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        print(f"[BehaviorTree/Docking] Battery critical! Navigating to dock at ({self.dock_x:.1f}, {self.dock_y:.1f})...")
        self._is_active = True

        # Phase 3: Navigate toward fixed dock coordinate
        res = drive_to(
            target_x=self.dock_x,
            target_y=self.dock_y,
            speed_mm_s=45.0,
            obstacle_avoidance=True,
            distance_tolerance_mm=10.0,
            timeout_s=12.0,
        )

        self._is_active = False

        if res.get("status") in ("success", "dry_run"):
            print("[BehaviorTree/Docking] Reached dock waypoint sector.")
            blackboard.set("is_docked", True)
            blackboard.set("last_action", "docked")
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        elif res.get("status") == "tripped":
            print(f"[BehaviorTree/Docking] Safety reflex intercepted docking drive: {res.get('error')}")
            self.status = NodeStatus.RUNNING  # Retry on next tick
            return NodeStatus.RUNNING
        else:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

    def cancel(self):
        super().cancel()
        self._is_active = False
