import threading
import time
import math
from typing import Callable, Optional
import cv2
import numpy as np
import pycozmo


class ReflexSafetyGuard:
    def __init__(self, cli: pycozmo.Client):
        self.cli = cli
        # Thread-safe flag to signal an active emergency reflex
        self.safety_tripped = threading.Event()
        self.last_event_reason = ""
        self.event_callbacks: list[Callable[[str], None]] = []

        # Internal state tracking
        self.is_picked_up = False
        self.cliff_detected = False
        self.is_falling = False
        self.bump_detected = False
        self.is_evasive_active = False
        self.is_docking_active = False
        self._evasive_thread_id: Optional[int] = None

        # Motor velocity tracking
        self.cmd_lwheel = 0.0
        self.cmd_rwheel = 0.0
        self.cmd_start_time = 0.0

        # Pose sliding window stall tracking
        self.pose_window_start_time = 0.0
        self.pose_window_ref_x = None
        self.pose_window_ref_y = None
        self.STALL_WINDOW_DURATION = 0.8  # seconds
        self.STALL_MIN_DISTANCE = 10.0    # mm

        # Visual Motion / Camera Bump Detection state tracking (3-second sliding reference window)
        self.visual_window_start_time = 0.0
        self.visual_window_ref_frame = None
        self.VISUAL_STALL_WINDOW_DURATION = 3.0  # seconds
        self.STALL_DIFF_THRESHOLD = 0.25  # Mean pixel difference threshold (below this = scene static)

        # Sensitivity thresholds for bump detection
        self.PITCH_BUMP_THRESHOLD = 0.35  # Radians (~20 degrees tilt upward)
        self.baseline_accel_x = -3600.0   # Adaptive resting baseline (mm/s^2)
        self.ACCEL_SHOCK_DELTA_THRESHOLD = -2200.0  # Deceleration shock below baseline (mm/s^2)

        # Lock to ensure only one evasive thread runs at a time
        self._worker_lock = threading.Lock()

        # Intercept motor control methods on PyCozmo client
        self._patch_client_motor_methods()

        # Listen to state updates AND specific change events
        self.cli.add_handler(pycozmo.event.EvtRobotStateUpdated, self._on_robot_state)
        self.cli.add_handler(pycozmo.event.EvtCliffDetectedChange, self._on_cliff_change)
        self.cli.add_handler(pycozmo.event.EvtRobotPickedUpChange, self._on_pickup_change)
        self.cli.add_handler(pycozmo.event.EvtRobotFallingChange, self._on_falling_change)
        try:
            self.cli.add_handler(pycozmo.event.EvtNewRawCameraImage, self._on_camera_image)
        except Exception:
            pass

    def _patch_client_motor_methods(self):
        """
        Intercepts drive_wheels, drive_straight, turn_in_place, and stop_all_motors
        on PyCozmo Client so that external host threads cannot issue movement commands
        while safety is tripped or evasive maneuver is executing, and tracks commanded speed.
        """
        if getattr(self.cli, "_is_safety_patched", False):
            self._orig_drive_wheels = getattr(self.cli, "_orig_drive_wheels", self.cli.drive_wheels)
            self._orig_stop_all_motors = getattr(self.cli, "_orig_stop_all_motors", self.cli.stop_all_motors)
            return

        orig_drive_wheels = self.cli.drive_wheels
        orig_drive_straight = getattr(self.cli, "drive_straight", None)
        orig_turn_in_place = getattr(self.cli, "turn_in_place", None)
        orig_stop_all_motors = self.cli.stop_all_motors

        self._orig_drive_wheels = orig_drive_wheels
        self._orig_stop_all_motors = orig_stop_all_motors

        self.cli._orig_drive_wheels = orig_drive_wheels
        self.cli._orig_stop_all_motors = orig_stop_all_motors

        def guarded_drive_wheels(lwheel_speed=0.0, rwheel_speed=0.0, *args, **kwargs):
            current_thread = threading.get_ident()
            if (self.safety_tripped.is_set() or self.is_evasive_active) and current_thread != self._evasive_thread_id:
                return
            l_val = float(lwheel_speed)
            r_val = float(rwheel_speed)
            self.cmd_lwheel = l_val
            self.cmd_rwheel = r_val
            if l_val != 0.0 or r_val != 0.0:
                if self.cmd_start_time == 0.0:
                    self.cmd_start_time = time.time()
            else:
                self.cmd_start_time = 0.0

            return orig_drive_wheels(lwheel_speed, rwheel_speed, *args, **kwargs)

        def guarded_drive_straight(distance, speed, *args, **kwargs):
            current_thread = threading.get_ident()
            if (self.safety_tripped.is_set() or self.is_evasive_active) and current_thread != self._evasive_thread_id:
                return
            s_val = float(speed)
            self.cmd_lwheel = s_val
            self.cmd_rwheel = s_val
            if s_val != 0.0 and self.cmd_start_time == 0.0:
                self.cmd_start_time = time.time()
            if orig_drive_straight:
                return orig_drive_straight(distance, speed, *args, **kwargs)

        def guarded_turn_in_place(angle, *args, **kwargs):
            current_thread = threading.get_ident()
            if (self.safety_tripped.is_set() or self.is_evasive_active) and current_thread != self._evasive_thread_id:
                return
            self.cmd_lwheel = -60.0
            self.cmd_rwheel = 60.0
            if orig_turn_in_place:
                return orig_turn_in_place(angle, *args, **kwargs)

        def guarded_stop_all_motors(*args, **kwargs):
            current_thread = threading.get_ident()
            if (self.safety_tripped.is_set() or self.is_evasive_active) and current_thread != self._evasive_thread_id:
                return
            self.cmd_lwheel = 0.0
            self.cmd_rwheel = 0.0
            self.cmd_start_time = 0.0
            return orig_stop_all_motors(*args, **kwargs)

        self.cli.drive_wheels = guarded_drive_wheels
        if orig_drive_straight:
            self.cli.drive_straight = guarded_drive_straight
        if orig_turn_in_place:
            self.cli.turn_in_place = guarded_turn_in_place
        self.cli.stop_all_motors = guarded_stop_all_motors

        self.cli._is_safety_patched = True

    def register_event_callback(self, callback: Callable[[str], None]):
        """Registers a callback function to report safety events up to higher behavior layers."""
        self.event_callbacks.append(callback)

    def _on_camera_image(self, cli, image):
        """Internal handler for PyCozmo EvtNewRawCameraImage event."""
        if image is None:
            return
        try:
            if hasattr(image, "convert"):
                bgr = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
            elif isinstance(image, np.ndarray):
                bgr = image
            else:
                bgr = np.array(image)

            is_fw = (self.cmd_lwheel > 20.0 and self.cmd_rwheel > 20.0)
            self.update_camera_frame(bgr, is_driving_forward=is_fw)
        except Exception:
            pass

    def update_camera_frame(self, bgr_image, is_driving_forward: Optional[bool] = None) -> bool:
        """
        Evaluates incoming camera frames across a 2-second reference window while forward movement is active.
        Triggers BUMP_DETECTED if scene has not changed after 2 full seconds of commanded forward driving.
        """
        now = time.time()

        if is_driving_forward is None:
            is_driving_forward = (self.cmd_lwheel > 20.0 and self.cmd_rwheel > 20.0)

        if bgr_image is None or not is_driving_forward or self.is_picked_up or self.is_evasive_active or getattr(self, "is_docking_active", False):
            self.visual_window_start_time = 0.0
            self.visual_window_ref_frame = None
            return False

        # Downscale, convert to grayscale, and Gaussian blur to eliminate CMOS sensor noise
        small = cv2.resize(bgr_image, (80, 60))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        if self.visual_window_start_time == 0.0 or self.visual_window_ref_frame is None:
            self.visual_window_start_time = now
            self.visual_window_ref_frame = blurred
            return False

        elapsed = now - self.visual_window_start_time
        if elapsed >= self.VISUAL_STALL_WINDOW_DURATION:
            # Calculate absolute mean difference against reference frame captured 3 seconds ago
            diff = float(cv2.absdiff(blurred, self.visual_window_ref_frame).mean())

            if diff < self.STALL_DIFF_THRESHOLD:
                self.visual_window_start_time = 0.0
                self.visual_window_ref_frame = None
                if not self.safety_tripped.is_set() and not getattr(self, "is_docking_active", False):
                    print(f"\n[REFLEX SAFETY] Visual stall detected after 3.0s (diff: {diff:.2f})! Driving into obstacle.")
                    self.bump_detected = True
                    self._trigger_evasive_reflex("BUMP_DETECTED")
                    return True
            else:
                # Robot moved over the 2.0s window. Reset reference frame for next 2-second window.
                self.visual_window_start_time = now
                self.visual_window_ref_frame = blurred

        return False

    def _on_robot_state(self, cli, state=None):
        """
        Runs on PyCozmo SDK packet thread context (~33Hz).
        Reads live telemetry directly from PyCozmo client objects.
        """
        now = time.time()

        status = (getattr(state, "status", None) if state is not None else None)
        if status is None:
            status = getattr(cli, "robot_status", 0) or 0

        self.cliff_detected = bool(status & pycozmo.robot.RobotStatusFlag.CLIFF_DETECTED)
        self.is_picked_up = getattr(cli, "robot_picked_up", False) or bool(
            status & pycozmo.robot.RobotStatusFlag.IS_PICKED_UP)
        self.is_falling = bool(status & pycozmo.robot.RobotStatusFlag.IS_FALLING)

        # Extract telemetry fields (supporting both PyCozmo RobotState packets & mock objects)
        pitch_rad = 0.0
        if state and hasattr(state, "pose_pitch_rad") and type(getattr(state, "pose_pitch_rad")).__name__ != "MagicMock":
            pitch_rad = float(getattr(state, "pose_pitch_rad"))
        else:
            obj = getattr(cli, "pose_pitch", None) or (getattr(state, "pose_pitch", None) if state else None)
            if obj:
                val = getattr(obj, "radians", obj)
                if val is not None and type(val).__name__ != "MagicMock":
                    try:
                        pitch_rad = float(val)
                    except (ValueError, TypeError):
                        pitch_rad = 0.0

        accel_x = 0.0
        if state and hasattr(state, "accel_x") and type(getattr(state, "accel_x")).__name__ != "MagicMock":
            accel_x = float(getattr(state, "accel_x"))
        else:
            obj = getattr(cli, "accel", None) or (getattr(state, "accel", None) if state else None)
            if obj:
                val = getattr(obj, "x", obj)
                if val is not None and type(val).__name__ != "MagicMock":
                    try:
                        accel_x = float(val)
                    except (ValueError, TypeError):
                        accel_x = 0.0

        l_speed = 0.0
        if state and hasattr(state, "lwheel_speed_mmps") and type(getattr(state, "lwheel_speed_mmps")).__name__ != "MagicMock":
            l_speed = float(getattr(state, "lwheel_speed_mmps"))
        else:
            obj = getattr(cli, "left_wheel_speed", None) or (getattr(state, "left_wheel_speed", None) if state else None)
            if obj:
                val = getattr(obj, "mmps", obj)
                if val is not None and type(val).__name__ != "MagicMock":
                    try:
                        l_speed = float(val)
                    except (ValueError, TypeError):
                        l_speed = 0.0

        pose_x, pose_y = None, None
        if state and hasattr(state, "pose_x") and hasattr(state, "pose_y") and type(getattr(state, "pose_x")).__name__ != "MagicMock":
            pose_x = float(getattr(state, "pose_x"))
            pose_y = float(getattr(state, "pose_y"))
        else:
            pose_obj = getattr(cli, "pose", None) or (getattr(state, "pose", None) if state else None)
            if pose_obj:
                pos = getattr(pose_obj, "position", pose_obj)
                if pos:
                    px = getattr(pos, "x", None)
                    py = getattr(pos, "y", None)
                    if px is not None and type(px).__name__ != "MagicMock":
                        try:
                            pose_x = float(px)
                        except (ValueError, TypeError):
                            pass
                    if py is not None and type(py).__name__ != "MagicMock":
                        try:
                            pose_y = float(py)
                        except (ValueError, TypeError):
                            pass

        is_forward_driving = (self.cmd_lwheel > 20.0 and self.cmd_rwheel > 20.0)


        # Adaptive resting baseline tracking when stationary
        if abs(l_speed) < 3.0 and not is_forward_driving:
            self.baseline_accel_x = 0.95 * self.baseline_accel_x + 0.05 * accel_x

        # (a) Pitch condition (climbing an object)
        is_pitched_up = abs(pitch_rad) > self.PITCH_BUMP_THRESHOLD

        # (b) Linear Acceleration Impact Shock (relative to resting baseline)
        gravity_x = math.sin(pitch_rad) * 9800.0
        true_accel_x = accel_x - gravity_x
        accel_shock = true_accel_x - self.baseline_accel_x

        is_impact_detected = False
        if is_forward_driving and accel_shock <= self.ACCEL_SHOCK_DELTA_THRESHOLD:
            is_impact_detected = True

        # (c) Pose Sliding Window Stall Detection
        is_stalled = False
        if is_forward_driving and pose_x is not None and pose_y is not None:
            if self.pose_window_start_time == 0.0 or self.pose_window_ref_x is None:
                self.pose_window_start_time = now
                self.pose_window_ref_x = pose_x
                self.pose_window_ref_y = pose_y
            else:
                elapsed = now - self.pose_window_start_time
                if elapsed >= self.STALL_WINDOW_DURATION:
                    dist_moved = math.hypot(pose_x - self.pose_window_ref_x, pose_y - self.pose_window_ref_y)
                    if dist_moved < self.STALL_MIN_DISTANCE:
                        is_stalled = True
                    else:
                        self.pose_window_start_time = now
                        self.pose_window_ref_x = pose_x
                        self.pose_window_ref_y = pose_y
        else:
            self.pose_window_start_time = 0.0
            self.pose_window_ref_x = None
            self.pose_window_ref_y = None

        if is_pitched_up or is_impact_detected or is_stalled:
            self.bump_detected = True

        if not self.is_picked_up:
            if self.cliff_detected and not self.safety_tripped.is_set():
                self._trigger_evasive_reflex("CLIFF_DETECTED")
            elif self.is_falling and not self.safety_tripped.is_set():
                self._trigger_evasive_reflex("IS_FALLING")
            elif self.bump_detected and not self.safety_tripped.is_set():
                if not getattr(self, "is_docking_active", False):
                    self._trigger_evasive_reflex("BUMP_DETECTED")
        else:
            if self.safety_tripped.is_set() and not self.is_evasive_active:
                if not self.cliff_detected and not self.is_falling and not self.bump_detected:
                    self.clear_safety()

    def _on_pickup_change(self, cli, state: bool):
        self.is_picked_up = bool(state)
        if self.is_picked_up:
            print("[REFLEX SAFETY] ROBOT PICKED UP! Halting motors.")
            self.safety_tripped.set()
            self.last_event_reason = "IS_PICKED_UP"
            try:
                self._orig_stop_all_motors()
            except Exception:
                pass
        else:
            print("[REFLEX SAFETY] Robot placed back on ground.")
            if not self.cliff_detected and not self.is_falling and not self.is_evasive_active:
                self.clear_safety()

    def _on_falling_change(self, cli, state: bool):
        self.is_falling = bool(state)
        if self.is_falling and not self.is_picked_up and not self.is_evasive_active:
            self._trigger_evasive_reflex("IS_FALLING")
        elif not self.is_falling and not self.cliff_detected and not self.is_picked_up and not self.is_evasive_active:
            self.clear_safety()

    def _on_cliff_change(self, cli, state: bool):
        self.cliff_detected = bool(state)
        if self.cliff_detected and not self.is_picked_up and not self.is_evasive_active:
            self._trigger_evasive_reflex("CLIFF_DETECTED")
        elif not self.cliff_detected and not self.is_falling and not self.is_picked_up and not self.is_evasive_active:
            self.clear_safety()

    def _trigger_evasive_reflex(self, reason: str):
        if self.is_evasive_active:
            return
        if getattr(self, "is_docking_active", False) and reason in ("BUMP_DETECTED", "IS_STALLED"):
            return
        self.safety_tripped.set()
        self.last_event_reason = reason
        self.is_evasive_active = True

        worker_thread = threading.Thread(target=self._evasive_worker, args=(reason,), daemon=True)
        worker_thread.start()

    def _evasive_worker(self, reason: str):
        self._evasive_thread_id = threading.get_ident()
        with self._worker_lock:
            print(f"[REFLEX SAFETY] {reason}! Executing non-blocking evasive maneuver...")

            def _pulse_drive(l_speed: float, r_speed: float, duration_s: float, step_interval_s: float = 0.08):
                t_start = time.time()
                while time.time() - t_start < duration_s:
                    if self.is_picked_up:
                        break
                    self.cli.drive_wheels(lwheel_speed=l_speed, rwheel_speed=r_speed)
                    time.sleep(step_interval_s)
                self.cli.drive_wheels(lwheel_speed=0.0, rwheel_speed=0.0)

            try:
                self.cli.drive_wheels(lwheel_speed=0.0, rwheel_speed=0.0)

                if reason == "CLIFF_DETECTED" and not self.is_picked_up:
                    BACKUP_DURATION = 1.2
                    TURN_DURATION = 0.9  # ~180° rotation at 80 mm/s differential speed

                    # 1. Back away from edge
                    _pulse_drive(-80.0, -80.0, BACKUP_DURATION)
                    time.sleep(0.2)

                    # 2. Spin 180° U-turn away from the cliff
                    _pulse_drive(80.0, -80.0, TURN_DURATION)

                elif reason == "BUMP_DETECTED" and not self.is_picked_up:
                    BACKUP_DURATION = 1.0
                    _pulse_drive(-80.0, -80.0, BACKUP_DURATION)

                elif reason == "IS_FALLING" and not self.is_picked_up:
                    self.cli.drive_wheels(lwheel_speed=0.0, rwheel_speed=0.0)

                for cb in self.event_callbacks:
                    try:
                        cb(reason)
                    except Exception as e:
                        print(f"[REFLEX SAFETY] Error in event callback: {e}")

            except Exception as e:
                print(f"[REFLEX SAFETY] Error during evasive maneuver: {e}")
            finally:
                self.is_evasive_active = False
                self._evasive_thread_id = None
                if not self.cliff_detected and not self.is_falling and not self.is_picked_up:
                    self.clear_safety()
                    print("[REFLEX SAFETY] Evasive maneuver complete. Surface safe. Safety cleared.")
                else:
                    print(f"[REFLEX SAFETY] Evasive maneuver complete. Active state: cliff={self.cliff_detected}, falling={self.is_falling}, pickup={self.is_picked_up}.")

    def is_safe(self) -> bool:
        return not self.safety_tripped.is_set() and not self.is_evasive_active

    def clear_safety(self):
        self.safety_tripped.clear()
        self.last_event_reason = ""
        self.bump_detected = False
        self.stuck_frame_count = 0
        self.last_gray_frame = None
        self.pose_window_start_time = 0.0
        self.pose_window_ref_x = None
        self.pose_window_ref_y = None

    def set_docking_mode(self, active: bool):
        """When docking is active, suppresses false bump/stall trips during ramp climbing."""
        self.is_docking_active = bool(active)
        if active:
            self.bump_detected = False
