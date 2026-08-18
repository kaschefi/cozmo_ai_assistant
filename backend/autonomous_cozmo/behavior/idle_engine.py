import time
import threading
from typing import Optional, Dict, Any, List

from .tree import Node, Selector, Sequence, Blackboard, NodeStatus
from .battery_monitor import battery_monitor, BatteryMonitor
from .nodes import (
    IsBatteryLowCondition,
    ExecuteDockingAction,
    SelectNextWanderTargetNode,
    ExecuteDriveToTargetNode,
    ExecuteIdleObservationNode,
)


class IdleBehaviorEngine:
    """
    Phase 3 Master Autonomous Idle Engine.
    Executes the top-level Behavior Tree asynchronously in a background loop,
    managing priority switching between Battery Recovery and Default Wander.
    """

    def __init__(
        self,
        tree_root: Optional[Node] = None,
        wander_waypoints: Optional[List[Dict[str, Any]]] = None,
        dock_coordinates: Optional[tuple] = None,
        tick_rate_hz: float = 5.0,
    ):
        self.blackboard = Blackboard()
        self.tick_interval_s = 1.0 / max(0.5, tick_rate_hz)

        # Build default Phase 3 Behavior Tree if no custom root is provided
        self.root = tree_root or self._build_default_phase3_tree(
            wander_waypoints=wander_waypoints,
            dock_coordinates=dock_coordinates,
        )

        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_tick_time = 0.0
        self._tick_count = 0

    def _build_default_phase3_tree(
        self,
        wander_waypoints: Optional[List[Dict[str, Any]]] = None,
        dock_coordinates: Optional[tuple] = None,
    ) -> Selector:
        """
        Builds the Phase 3 Priority Selector:
        Priority 1: Battery Low -> Navigate to Dock
        Priority 2: Default -> Wander Waypoint Sequence
        """
        dock_x, dock_y = dock_coordinates if dock_coordinates else (0.0, 0.0)

        # Priority 1: Battery Recovery Branch
        battery_branch = Sequence("BatteryRecoverySequence", [
            IsBatteryLowCondition("CheckBatteryLevel"),
            ExecuteDockingAction("DockAtCharger", dock_x=dock_x, dock_y=dock_y),
        ])

        # Priority 2: Default Wander Branch
        wander_branch = Sequence("IdleWanderSequence", [
            SelectNextWanderTargetNode("SelectTarget", waypoints=wander_waypoints),
            ExecuteDriveToTargetNode("DriveToTarget"),
            ExecuteIdleObservationNode("IdleObservation"),
        ])

        # Root Selector: Evaluates Battery branch first, falls back to Wander
        root = Selector("Phase3_AutonomousRoot", [
            battery_branch,
            wander_branch,
        ])
        return root

    def tick_once(self) -> NodeStatus:
        """Executes a single synchronous tick of the Behavior Tree."""
        with self._lock:
            self._tick_count += 1
            self._last_tick_time = time.time()
            status = self.root.tick(self.blackboard)
            self.blackboard.set("last_tree_status", status.value)
            self.blackboard.set("tick_count", self._tick_count)
            return status

    def start(self):
        """Starts the autonomous idle behavior tree execution loop in a background thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._paused = False
            self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="IdleBehaviorEngineThread")
            self._thread.start()
            print("[IdleBehaviorEngine] Autonomous behavior tree engine started.")

    def pause(self):
        """Pauses autonomous idle execution (e.g. when higher-priority voice action takes control)."""
        with self._lock:
            if not self._paused:
                self._paused = True
                print("[IdleBehaviorEngine] Engine paused.")

    def resume(self):
        """Resumes autonomous idle execution."""
        with self._lock:
            if self._paused:
                self._paused = False
                print("[IdleBehaviorEngine] Engine resumed.")

    def stop(self):
        """Stops the autonomous idle behavior tree execution loop."""
        with self._lock:
            if not self._running:
                return
            self._running = False
            self._paused = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.root.cancel()
        print("[IdleBehaviorEngine] Autonomous behavior tree engine stopped.")

    def is_running(self) -> bool:
        with self._lock:
            return self._running and not self._paused

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "paused": self._paused,
                "tick_count": self._tick_count,
                "last_tick_time": self._last_tick_time,
                "blackboard": self.blackboard.snapshot(),
                "battery": battery_monitor.get_telemetry_status(),
            }

    def _worker_loop(self):
        while self._running:
            if not self._paused:
                try:
                    self.tick_once()
                except Exception as e:
                    print(f"[IdleBehaviorEngine] Error during tree tick: {e}")

            time.sleep(self.tick_interval_s)


# Global singleton IdleBehaviorEngine
idle_engine = IdleBehaviorEngine()
