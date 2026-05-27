import pycozmo
import threading
import time


class CozmoManager:
    _instance = None
    cli = None
    robot_mode = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CozmoManager, cls).__new__(cls)
            cls._instance.robot_mode = False
        return cls._instance

    def start(self):
        def connect():
            self.cli = pycozmo.Client()
            self.cli.start()
            self.cli.connect()
            self.cli.wait_for_robot()
            print("PyCozmo connected")
            # Automatically raise the head to horizontal looking straight forward
            # to override the default firmware calibration downward sag
            try:
                self.cli.set_head_angle(0.7)
            except Exception as e:
                print(f"Failed to auto-raise head: {e}")

        threading.Thread(target=connect, daemon=True).start()

    def get_robot(self):
        return self.cli


cozmo_manager = CozmoManager()