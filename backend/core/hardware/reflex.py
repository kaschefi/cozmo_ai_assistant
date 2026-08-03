import threading
import time
from typing import Callable, Optional
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
        self.is_evasive_active = False
        self._evasive_thread_id: Optional[int] = None

        # Lock to ensure only one evasive thread runs at a time
        self._worker_lock = threading.Lock()

        # Intercept motor control methods on PyCozmo client
        self._patch_client_motor_methods()

        # Listen to state updates AND specific change events
        self.cli.add_handler(pycozmo.event.EvtRobotStateUpdated, self._on_robot_state)
        self.cli.add_handler(pycozmo.event.EvtCliffDetectedChange, self._on_cliff_change)
        self.cli.add_handler(pycozmo.event.EvtRobotPickedUpChange, self._on_pickup_change)
        self.cli.add_handler(pycozmo.event.EvtRobotFallingChange, self._on_falling_change)

    def _patch_client_motor_methods(self):
        """
        Intercepts drive_wheels, drive_straight, turn_in_place, and stop_all_motors
        on PyCozmo Client so that external host threads cannot issue movement commands
        while safety is tripped or evasive maneuver is executing.
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

        def guarded_drive_wheels(*args, **kwargs):
            current_thread = threading.get_ident()
            if (self.safety_tripped.is_set() or self.is_evasive_active) and current_thread != self._evasive_thread_id:
                return
            return orig_drive_wheels(*args, **kwargs)

        def guarded_drive_straight(*args, **kwargs):
            current_thread = threading.get_ident()
            if (self.safety_tripped.is_set() or self.is_evasive_active) and current_thread != self._evasive_thread_id:
                return
            if orig_drive_straight:
                return orig_drive_straight(*args, **kwargs)

        def guarded_turn_in_place(*args, **kwargs):
            current_thread = threading.get_ident()
            if (self.safety_tripped.is_set() or self.is_evasive_active) and current_thread != self._evasive_thread_id:
                return
            if orig_turn_in_place:
                return orig_turn_in_place(*args, **kwargs)

        def guarded_stop_all_motors(*args, **kwargs):
            current_thread = threading.get_ident()
            if (self.safety_tripped.is_set() or self.is_evasive_active) and current_thread != self._evasive_thread_id:
                return
            return orig_stop_all_motors(*args, **kwargs)

        self.cli.drive_wheels = guarded_drive_wheels
        if orig_drive_straight:
            self.cli.drive_straight = guarded_drive_straight
        if orig_turn_in_place:
            self.cli.turn_in_place = guarded_turn_in_place
        self.cli.stop_all_motors = guarded_stop_all_motors

        self.cli._is_safety_patched = True

    def register_event_callback(self, callback: Callable[[str], None]):
        """
        Registers a callback function to report safety events up to higher behavior layers.
        """
        self.event_callbacks.append(callback)

    def _on_robot_state(self, cli, state=None):
        """
        Runs on PyCozmo SDK packet thread context (~33Hz).
        Inspects status flags continuously.
        """
        status = getattr(state, "status", getattr(cli, "robot_status", 0)) or 0
        self.cliff_detected = bool(status & pycozmo.robot.RobotStatusFlag.CLIFF_DETECTED)
        self.is_picked_up = bool(status & pycozmo.robot.RobotStatusFlag.IS_PICKED_UP)
        self.is_falling = bool(status & pycozmo.robot.RobotStatusFlag.IS_FALLING)

        if self.is_picked_up:
            if not self.safety_tripped.is_set():
                self.safety_tripped.set()
                self.last_event_reason = "IS_PICKED_UP"
                try:
                    self._orig_stop_all_motors()
                except Exception:
                    pass
        else:
            if self.cliff_detected and not self.safety_tripped.is_set() and not self.is_evasive_active:
                self._trigger_evasive_reflex("CLIFF_DETECTED")
            elif self.is_falling and not self.safety_tripped.is_set() and not self.is_evasive_active:
                self._trigger_evasive_reflex("IS_FALLING")

    def _on_pickup_change(self, cli, state: bool):
        """
        Triggered instantly when pickup status changes.
        """
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
        """
        Triggered instantly when freefall state changes.
        """
        self.is_falling = bool(state)
        if self.is_falling and not self.is_picked_up and not self.is_evasive_active:
            self._trigger_evasive_reflex("IS_FALLING")
        elif not self.is_falling and not self.cliff_detected and not self.is_picked_up and not self.is_evasive_active:
            self.clear_safety()

    def _on_cliff_change(self, cli, state: bool):
        """
        Triggered instantly when cliff sensor status changes.
        """
        self.cliff_detected = bool(state)
        if self.cliff_detected and not self.is_picked_up and not self.is_evasive_active:
            self._trigger_evasive_reflex("CLIFF_DETECTED")
        elif not self.cliff_detected and not self.is_falling and not self.is_picked_up and not self.is_evasive_active:
            self.clear_safety()

    def _trigger_evasive_reflex(self, reason: str):
        if self.is_evasive_active:
            return
        self.safety_tripped.set()
        self.last_event_reason = reason
        self.is_evasive_active = True

        # Spawn non-blocking background thread for wheel movement so SDK packet thread is never frozen!
        worker_thread = threading.Thread(target=self._evasive_worker, args=(reason,), daemon=True)
        worker_thread.start()

    def _evasive_worker(self, reason: str):
        self._evasive_thread_id = threading.get_ident()
        with self._worker_lock:
            print(f"[REFLEX SAFETY] {reason}! Executing non-blocking evasive backup & U-turn...")

            try:
                # Force immediate halt
                self.cli.drive_wheels(lwheel_speed=0.0, rwheel_speed=0.0)

                if reason == "CLIFF_DETECTED" and not self.is_picked_up:
                    BACKUP_DURATION = 1.2
                    TURN_DURATION = 1.5

                    # Step 1: Back away from the cliff edge
                    if not self.is_picked_up:
                        self.cli.drive_wheels(lwheel_speed=-80.0, rwheel_speed=-80.0)
                        time.sleep(BACKUP_DURATION)

                    # Step 2: Intermediate brake
                    if not self.is_picked_up:
                        self.cli.drive_wheels(lwheel_speed=0.0, rwheel_speed=0.0)
                        time.sleep(0.3)

                    # Step 3: 180° U-turn away from edge
                    if not self.is_picked_up:
                        self.cli.drive_wheels(lwheel_speed=100.0, rwheel_speed=-100.0)
                        time.sleep(TURN_DURATION)

                    # Step 4: Final brake
                    self.cli.drive_wheels(lwheel_speed=0.0, rwheel_speed=0.0)

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