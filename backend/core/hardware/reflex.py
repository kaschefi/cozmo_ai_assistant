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

        # Hook into PyCozmo's native packet reception event (runs on SDK packet thread)
        self.cli.add_handler(pycozmo.event.EvtRobotStateUpdated, self._on_robot_state)

    def register_event_callback(self, callback: Callable[[str], None]):
        """
        Registers a callback function to report safety events up to higher behavior layers.
        """
        self.event_callbacks.append(callback)

    def _on_robot_state(self, cli, state=None):
        """
        Runs inside PyCozmo's low-level packet thread context.
        Zero lag, raw hardware speed (~33Hz telemetry rate).
        """
        status = getattr(state, "status", getattr(cli, "robot_status", 0)) or 0

        cliff_detected = bool(status & pycozmo.robot.RobotStatusFlag.CLIFF_DETECTED)
        is_picked_up = bool(status & pycozmo.robot.RobotStatusFlag.IS_PICKED_UP)
        is_falling = bool(status & pycozmo.robot.RobotStatusFlag.IS_FALLING)

        if not is_picked_up:
            if cliff_detected:
                if not self.safety_tripped.is_set():
                    self._execute_reflex("CLIFF_DETECTED")
            elif is_falling:
                if not self.safety_tripped.is_set():
                    self._execute_reflex("IS_FALLING")

    def _execute_reflex(self, reason: str):
        # 1. Instantly set the guard flag to block incoming host movement packets
        self.safety_tripped.set()
        self.last_event_reason = reason

        print(f"[REFLEX SAFETY] {reason}! Intercepting track control...")

        # 2. Bypass host thread and hit emergency brakes
        self.cli.drive_wheels(lwheel_speed=0.0, rwheel_speed=0.0)

        # 3. Fire backup maneuver immediately if cliff detected
        if reason == "CLIFF_DETECTED":
            self.cli.drive_wheels(lwheel_speed=-50.0, rwheel_speed=-50.0, duration=0.5)

        # 4. Report event up to behavior layer
        for cb in self.event_callbacks:
            try:
                cb(reason)
            except Exception as e:
                print(f"[REFLEX SAFETY] Error in event callback: {e}")

    def is_safe(self) -> bool:
        return not self.safety_tripped.is_set()

    def clear_safety(self):
        self.safety_tripped.clear()
        self.last_event_reason = ""