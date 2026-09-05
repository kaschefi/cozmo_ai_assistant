import pycozmo
import threading
import time
from core.hardware.safety import ReflexSafetyGuard


class CozmoManager:
    _instance = None
    cli = None
    safety_guard = None
    _is_connected = False
    is_connecting = False
    robot_mode = False
    latest_image = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CozmoManager, cls).__new__(cls)
            cls._instance.robot_mode = False
            cls._instance.safety_guard = None
            cls._instance._is_connected = False
            cls._instance.is_connecting = False
            cls._instance.latest_image = None
        return cls._instance

    @property
    def is_connected(self) -> bool:
        if not self._is_connected or not self.cli:
            return False
        # Verify active PyCozmo socket state if available
        if hasattr(self.cli, "conn") and self.cli.conn:
            connected_const = getattr(self.cli.conn, "CONNECTED", 3)
            current_state = getattr(self.cli.conn, "state", None)
            if current_state is not None and current_state != connected_const:
                self._is_connected = False
                return False
        return self._is_connected

    @is_connected.setter
    def is_connected(self, value: bool):
        self._is_connected = bool(value)

    def start(self):
        if self.is_connected and self.cli:
            return
        if self.is_connecting:
            return

        self.is_connecting = True

        def connect():
            try:
                cli = pycozmo.Client()
                cli.start()
                cli.connect()
                print("Waiting for Cozmo robot Wi-Fi handshake...")
                cli.wait_for_robot()
                self.cli = cli
                self.is_connected = True
                self.is_connecting = False
                print("[OK] PyCozmo connected successfully!")

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

                # Enable camera stream and attach frame handler for DINO & visual anchors
                try:
                    def _on_camera_frame(client, image):
                        client.latest_image = image
                        client._latest_image = image
                        self.latest_image = image

                    self.cli.add_handler(pycozmo.event.EvtNewRawCameraImage, _on_camera_frame)
                    self.cli.enable_camera(enable=True, color=True)
                    self.cli._cam_stream_enabled = True
                    print("[OK] [Camera] Stream enabled (color=True) & EvtNewRawCameraImage handler registered.")
                except Exception as e:
                    print(f"Failed to enable camera stream: {e}")

            except pycozmo.exception.ConnectionTimeout:
                self.is_connected = False
                self.is_connecting = False
                self.cli = None
                print("[PyCozmo Error] Connection Timeout!")
                print("   Please verify:")
                print("   1. Cozmo is turned ON (head lights lit up).")
                print("   2. Your computer Wi-Fi is connected to Cozmo's Wi-Fi network (e.g. Cozmo_XXXXXX).")
            except Exception as e:
                self.is_connected = False
                self.is_connecting = False
                self.cli = None
                print(f"[PyCozmo Error] Failed to connect to Cozmo: {e}")

        threading.Thread(target=connect, daemon=True).start()

    def wait_for_connection(self, timeout: float = 15.0):
        """
        Wait for background connection thread to finish Wi-Fi handshake.
        Returns the PyCozmo client instance if connected, or None if timed out.
        """
        start_t = time.time()
        attempt = 1
        while time.time() - start_t < timeout:
            if self.is_connected and self.cli:
                return self.cli
            if not self.is_connecting and not self.is_connected:
                # Thread finished with an error
                return None
            time.sleep(0.5)
            attempt += 1
        return self.cli if self.is_connected else None

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

    def set_docking_mode(self, active: bool):
        """Notifies the safety guard of active docking to prevent false bump triggers."""
        guard = self.get_safety_guard()
        if guard and hasattr(guard, "set_docking_mode"):
            guard.set_docking_mode(active)




    def disconnect(self):
        """Safely disconnect and stop the PyCozmo client."""
        if self.cli:
            try:
                self.cli.disconnect()
            except Exception as e:
                print(f"[PyCozmo] Disconnect notice: {e}")
            try:
                self.cli.stop()
            except Exception as e:
                print(f"[PyCozmo] Stop notice: {e}")
        self.cli = None
        self.is_connected = False
        self.is_connecting = False
        self.robot_mode = False
        self.safety_guard = None
        self.latest_image = None
        print("[PyCozmo] Disconnected successfully.")


cozmo_manager = CozmoManager()
