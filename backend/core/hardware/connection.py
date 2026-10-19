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
    last_error = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CozmoManager, cls).__new__(cls)
            cls._instance.robot_mode = False
            cls._instance.safety_guard = None
            cls._instance._is_connected = False
            cls._instance.is_connecting = False
            cls._instance.latest_image = None
            cls._instance.last_error = None
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
        self.last_error = None

        def connect():
            cli = None
            try:
                cli = pycozmo.Client()
                cli.start()
                cli.connect()
                print("Waiting for Cozmo robot Wi-Fi handshake...")
                cli.wait_for_robot()
                self.cli = cli
                self.is_connected = True
                self.is_connecting = False
                self.last_error = None
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
                self.last_error = "Connection Timeout: Cozmo robot not found. Verify robot is ON and PC is connected to Cozmo_XXXXXX Wi-Fi."
                print("[PyCozmo Error] Connection Timeout!")
                print("   Please verify:")
                print("   1. Cozmo is turned ON (head lights lit up).")
                print("   2. Your computer Wi-Fi is connected to Cozmo's Wi-Fi network (e.g. Cozmo_XXXXXX).")
            except Exception as e:
                self.is_connected = False
                self.is_connecting = False
                self.cli = None
                self.last_error = f"Failed to connect to Cozmo: {e}"
                print(f"[PyCozmo Error] Failed to connect to Cozmo: {e}")
            finally:
                if not self.is_connected and cli:
                    try:
                        cli.disconnect()
                    except Exception:
                        pass
                    try:
                        cli.stop()
                    except Exception:
                        pass

        threading.Thread(target=connect, daemon=True).start()

    def wait_for_connection(self, timeout: float = 15.0):
        """
        Wait for background connection thread to finish Wi-Fi handshake.
        Returns the PyCozmo client instance if connected, or None if timed out.
        """
        start_t = time.time()
        while time.time() - start_t < timeout:
            if self.is_connected and self.cli:
                return self.cli
            if not self.is_connecting and not self.is_connected:
                # Thread finished with an error
                return None
            time.sleep(0.3)

        # Timed out waiting
        self.is_connecting = False
        if not self.is_connected and not self.last_error:
            self.last_error = "Connection timed out. Robot not found on Wi-Fi."
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

    def set_undocking_mode(self, active: bool):
        """Notifies safety guard of active undocking to suppress cliff triggers during charger roll-off."""
        guard = self.get_safety_guard()
        if guard and hasattr(guard, "set_undocking_mode"):
            guard.set_undocking_mode(active)

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
        self.last_error = None
        print("[PyCozmo] Disconnected successfully.")


cozmo_manager = CozmoManager()
