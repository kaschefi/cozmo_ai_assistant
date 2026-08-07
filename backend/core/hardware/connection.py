import pycozmo
import threading
import time
from core.hardware.safety import ReflexSafetyGuard


class CozmoManager:
    _instance = None
    cli = None
    safety_guard = None
    is_connected = False
    robot_mode = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CozmoManager, cls).__new__(cls)
            cls._instance.robot_mode = False
            cls._instance.safety_guard = None
            cls._instance.is_connected = False
        return cls._instance

    def start(self):
        def connect():
            try:
                cli = pycozmo.Client()
                cli.start()
                cli.connect()
                print("Waiting for Cozmo robot Wi-Fi handshake...")
                cli.wait_for_robot()
                self.cli = cli
                self.is_connected = True
                print("✅ PyCozmo connected successfully!")

                # Initialize safety reflex guard
                self.safety_guard = ReflexSafetyGuard(self.cli)
                try:
                    from core.routing.layer1.registry import reflex_registry
                    reflex_registry.safety_guard = self.safety_guard
                except Exception as e:
                    print(f"Could not register safety_guard on reflex_registry: {e}")

                # Automatically raise head to horizontal
                try:
                    self.cli.set_head_angle(0.7)
                except Exception as e:
                    print(f"Failed to auto-raise head: {e}")

            except pycozmo.exception.ConnectionTimeout:
                self.is_connected = False
                self.cli = None
                print("❌ [PyCozmo Error] Connection Timeout!")
                print("   Please verify:")
                print("   1. Cozmo is turned ON (head lights lit up).")
                print("   2. Your computer Wi-Fi is connected to Cozmo's Wi-Fi network (e.g. Cozmo_XXXXXX).")
            except Exception as e:
                self.is_connected = False
                self.cli = None
                print(f"❌ [PyCozmo Error] Failed to connect to Cozmo: {e}")

        threading.Thread(target=connect, daemon=True).start()

    def get_robot(self):
        return self.cli if self.is_connected else None

    def get_safety_guard(self):
        if self.cli and self.is_connected and not self.safety_guard:
            self.safety_guard = ReflexSafetyGuard(self.cli)
            try:
                from core.routing.layer1.registry import reflex_registry
                reflex_registry.safety_guard = self.safety_guard
            except Exception:
                pass
        return self.safety_guard




cozmo_manager = CozmoManager()