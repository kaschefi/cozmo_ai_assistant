import time
import threading
from typing import Optional, Dict, Any, List
import pycozmo

from .tree import Node, Selector, Sequence, Blackboard, NodeStatus
from .battery_monitor import battery_monitor, BatteryMonitor
from .nodes.battery_nodes import IsBatteryLowCondition, ExecuteDockingAction
from .nodes.slam_nodes import CheckVisibleAnchorCondition, ExecuteSLAMOffsetCorrectionAction
from .nodes.wander_nodes import (
    SelectDynamicWanderTargetNode,
    SelectNextWanderTargetNode,
    ExecuteDriveToTargetNode,
    ExecuteIdleObservationNode,
)
from ..vision.remind_engine import remind_engine
from ..motion.pose_tracker import pose_tracker
from core.hardware.connection import cozmo_manager


class IdleBehaviorEngine:
    """
    Phase 4 Master Autonomous Idle Engine.
    Executes the top-level Behavior Tree asynchronously in a background loop:
    - Priority 1: Battery Critical Recovery & Docking
    - Priority 2: Visual Landmark SLAM Drift Correction (Odometry alignment)
    - Priority 3: Dynamic REMIND Visual Memory Wander Exploration
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

        # Build default Phase 4 Behavior Tree if no custom root is provided
        self.root = tree_root or self._build_default_phase4_tree(
            wander_waypoints=wander_waypoints,
            dock_coordinates=dock_coordinates,
        )

        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_tick_time = 0.0
        self._tick_count = 0
        self._camera_handler_attached = False

    def _build_default_phase4_tree(
        self,
        wander_waypoints: Optional[List[Dict[str, Any]]] = None,
        dock_coordinates: Optional[tuple] = None,
    ) -> Selector:
        """
        Builds the Phase 4 Priority Selector:
        Priority 1: Battery Low -> Navigate to Dock
        Priority 2: Landmark SLAM -> Correct Odometry Drift
        Priority 3: Dynamic REMIND -> Novelty & Revisit Exploration
        """
        dock_x, dock_y = dock_coordinates if dock_coordinates else (0.0, 0.0)

        # Priority 1: Battery Recovery Branch
        battery_branch = Sequence("BatteryRecoverySequence", [
            IsBatteryLowCondition("CheckBatteryLevel"),
            ExecuteDockingAction("DockAtCharger", dock_x=dock_x, dock_y=dock_y),
        ])

        # Priority 2: Visual Landmark SLAM Drift Correction
        slam_branch = Sequence("VisualSLAMDriftCorrectionSequence", [
            CheckVisibleAnchorCondition("CheckVisibleAnchor", landmark_name="ChargingDock"),
            ExecuteSLAMOffsetCorrectionAction("ApplySLAMDriftOffset"),
        ])

        # Priority 3: Dynamic REMIND Wander Branch
        wander_branch = Sequence("DynamicREMINDWanderSequence", [
            SelectDynamicWanderTargetNode("SelectTarget", fallback_waypoints=wander_waypoints),
            ExecuteDriveToTargetNode("DriveToTarget"),
            ExecuteIdleObservationNode("IdleObservation"),
        ])

        # Root Selector: Evaluates Battery -> SLAM -> Dynamic Wander
        root = Selector("Phase4_AutonomousRoot", [
            battery_branch,
            slam_branch,
            wander_branch,
        ])
        return root

    # Alias for backward compatibility
    _build_default_phase3_tree = _build_default_phase4_tree

    def _on_camera_frame(self, cli, raw_image):
        """Asynchronously feeds camera frames to REMIND memory without blocking."""
        if not self._running or self._paused:
            return
        pose = pose_tracker.get_effective_pose()
        remind_engine.process_frame_async(raw_image, pose)

    def _attach_camera_stream(self):
        if self._camera_handler_attached:
            return
        cli = cozmo_manager.get_robot()
        if cli:
            try:
                cli.add_handler(pycozmo.event.EvtNewRawCameraImage, self._on_camera_frame)
                self._camera_handler_attached = True
            except Exception:
                pass

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
            self._attach_camera_stream()
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

            # Cancel active nodes
            if self.root:
                self.root.cancel()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        print("[IdleBehaviorEngine] Autonomous behavior tree engine stopped.")

    def _worker_loop(self):
        """Continuous execution worker loop ticking the behavior tree at tick_rate_hz."""
        while self._running:
            loop_start = time.time()

            if not self._paused:
                try:
                    self.tick_once()
                except Exception as e:
                    print(f"[IdleBehaviorEngine Error] Exception during tree tick: {e}")

            elapsed = time.time() - loop_start
            sleep_time = max(0.01, self.tick_interval_s - elapsed)
            time.sleep(sleep_time)

    def is_running(self) -> bool:
        with self._lock:
            return self._running and not self._paused


# Global singleton IdleBehaviorEngine
idle_engine = IdleBehaviorEngine()

