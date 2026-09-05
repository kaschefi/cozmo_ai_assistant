import time
import math
from typing import Optional, Tuple, Dict, Any, List
from ..tree import Node, NodeStatus, Blackboard
from ..battery_monitor import battery_monitor
from ...motion import (
    drive_to,
    follow_path,
    pose_tracker,
    bidirectional_astar_planner,
    DEFAULT_SAFETY_CLEARANCE_MM,
)
from ...vision import visual_anchor_store, get_default_charger_pose
try:
    import pycozmo
except ImportError:
    pycozmo = None
from core.hardware.connection import cozmo_manager
from ...motion.visual_servoing import check_robot_on_charger


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
    Action Node (Phase 5 Autonomous Docking):
    1. Retrieves Charger spatial anchor from visual memory.
    2. Plans optimal collision-free path with 5cm clearance using Two-Way (Bidirectional) A*.
    3. Traverses waypoints to the pre-dock alignment point in front of the charger.
    4. Executes the precise 180° rotation and reverse docking onto the pins.
    """
    def __init__(
        self,
        name: str = "ExecuteDockingAction",
        dock_x: Optional[float] = None,
        dock_y: Optional[float] = None,
        dock_theta: Optional[float] = None,
        safety_clearance_mm: float = DEFAULT_SAFETY_CLEARANCE_MM,
    ):
        super().__init__(name)
        self.override_x = dock_x
        self.override_y = dock_y
        self.override_theta = dock_theta
        self.safety_clearance_mm = float(safety_clearance_mm)
        self._is_active = False

    def _get_target_charger_pose(self, current_pose: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Resolves target charger coordinates from visual anchors or default behind Cozmo."""
        if self.override_x is not None and self.override_y is not None:
            return float(self.override_x), float(self.override_y), float(self.override_theta or 180.0)

        # Check visual anchor store
        for label in ("charger", "ChargingDock", "charging_dock", "dock"):
            anchor = visual_anchor_store.get_anchor(label)
            if anchor and (anchor.estimated_x != 0.0 or anchor.estimated_y != 0.0):
                return anchor.estimated_x, anchor.estimated_y, anchor.estimated_theta_deg

        # Default 10 cm behind current pose
        return get_default_charger_pose(current_pose)

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if blackboard.get("is_docked", False):
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        self._is_active = True
        curr_pose = pose_tracker.get_effective_pose()
        charger_pose = self._get_target_charger_pose(curr_pose)

        # Gather registered blocks / obstacles
        obstacles_data: List[Dict[str, Any]] = []
        for obs in visual_anchor_store.list_obstacles():
            obstacles_data.append({
                "x": obs.x,
                "y": obs.y,
                "radius": obs.radius,
                "label": "Obstacle",
            })
        for anc in visual_anchor_store.list_anchors():
            if not any(tag in anc.label.lower() for tag in ("charger", "dock")):
                obstacles_data.append({
                    "x": anc.estimated_x,
                    "y": anc.estimated_y,
                    "radius": 25.0,
                    "label": anc.label,
                })

        print(f"[BehaviorTree/Docking] Planning 2-Way A* path from {curr_pose[:2]} to charger at {charger_pose[:2]} with 5cm clearance...")

        # Compute Bidirectional A* path
        plan = bidirectional_astar_planner.plan_docking_path(
            start_pose=curr_pose,
            charger_pose=charger_pose,
            obstacles=obstacles_data,
            custom_clearance_mm=self.safety_clearance_mm,
        )

        blackboard.set("planned_dock_path", plan.waypoints)

        if not plan.success:
            print(f"[BehaviorTree/Docking] Path planner failed: {plan.message}")
            self.status = NodeStatus.FAILURE
            self._is_active = False
            return NodeStatus.FAILURE

        print(f"[BehaviorTree/Docking] Trajectory found: {len(plan.waypoints)} waypoints, {plan.total_length_mm:.0f}mm length.")

        # Follow waypoints to pre-dock approach entrance
        # Intermediate waypoints (excluding final pin contact)
        approach_waypoints = plan.waypoints[:-1] if len(plan.waypoints) > 1 else plan.waypoints
        res = follow_path(
            waypoints=approach_waypoints,
            speed_mm_s=45.0,
            obstacle_avoidance=True,
            obstacles=obstacles_data,
            distance_tolerance_mm=15.0,
        )

        if res.get("status") == "tripped":
            print(f"[BehaviorTree/Docking] Safety reflex active: {res.get('error')}")
            self.status = NodeStatus.RUNNING
            return NodeStatus.RUNNING
        elif res.get("status") not in ("success", "dry_run"):
            print(f"[BehaviorTree/Docking] Waypoint execution failed: {res.get('error')}")
            self.status = NodeStatus.FAILURE
            self._is_active = False
            return NodeStatus.FAILURE

        print("[BehaviorTree/Docking] Reached charger approach node. Executing 180° reverse dock into charging cradle...")
        cli = cozmo_manager.get_robot() if cozmo_manager.is_connected else None
        target_reverse_theta = (charger_pose[2] + 180.0) % 360.0

        if cli:
            try:
                cozmo_manager.set_docking_mode(True)
                if pycozmo:
                    cli.set_lift_height(pycozmo.robot.MIN_LIFT_HEIGHT.mm)
                cli.set_head_angle(0.0)

                # Turn 180°
                curr_th_deg = math.degrees(pose_tracker.theta)
                diff_rot = (target_reverse_theta - curr_th_deg + 180.0) % 360.0 - 180.0
                if abs(diff_rot) > 2.5:
                    turn_dir = 1.0 if diff_rot > 0 else -1.0
                    turn_speed_deg_s = 60.0
                    turn_time = abs(diff_rot) / turn_speed_deg_s
                    wheel_spd = math.radians(turn_speed_deg_s) * (45.0 / 2.0)
                    cli.drive_wheels(lwheel_speed=-turn_dir * wheel_spd, rwheel_speed=turn_dir * wheel_spd)
                    time.sleep(turn_time)
                    cli.stop_all_motors()
                    pose_tracker.update_relative_motion(0.0, diff_rot)
                    time.sleep(0.1)

                # Reverse onto pins
                dock_speed = -25.0
                cli.drive_wheels(lwheel_speed=dock_speed, rwheel_speed=dock_speed)
                contact_made = False
                for _ in range(35):
                    if check_robot_on_charger(cli):
                        contact_made = True
                        print("[BehaviorTree/Docking] Real charger pin contact confirmed (IS_ON_CHARGER=True)!")
                        break
                    time.sleep(0.1)

                cli.stop_all_motors()

                # Retry nudge if contact not confirmed
                if not contact_made:
                    print("[BehaviorTree/Docking] Retrying pin seating with forward nudge...")
                    cli.drive_wheels(lwheel_speed=20.0, rwheel_speed=20.0)
                    time.sleep(0.6)
                    cli.stop_all_motors()
                    cli.drive_wheels(lwheel_speed=-28.0, rwheel_speed=-28.0)
                    for _ in range(25):
                        if check_robot_on_charger(cli):
                            contact_made = True
                            print("[BehaviorTree/Docking] Charger contact verified after nudge!")
                            break
                        time.sleep(0.08)
                    cli.stop_all_motors()

            except Exception as e:
                print(f"[BehaviorTree/Docking] Physical docking notice: {e}")
            finally:
                cozmo_manager.set_docking_mode(False)
        else:
            pose_tracker.update_pose(charger_pose[0], charger_pose[1], target_reverse_theta)

        blackboard.set("is_docked", True)
        blackboard.set("last_action", "docked")
        self.status = NodeStatus.SUCCESS
        self._is_active = False
        return NodeStatus.SUCCESS

    def cancel(self):
        super().cancel()
        self._is_active = False
