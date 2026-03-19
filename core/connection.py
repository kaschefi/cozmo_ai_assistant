import pycozmo
import threading
import time


class CozmoManager:
    _instance = None
    cli = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CozmoManager, cls).__new__(cls)
        return cls._instance

    def start(self):
        def connect():
            self.cli = pycozmo.Client()
            self.cli.start()
            self.cli.connect()
            self.cli.wait_for_robot()
            print("PyCozmo connected")

        threading.Thread(target=connect, daemon=True).start()

    def get_robot(self):
        return self.cli


cozmo_manager = CozmoManager()