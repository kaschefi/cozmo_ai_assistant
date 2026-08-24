"""
Unit Tests for Cozmo Autonomous Vision & Mission Control REST API (/api/cozmo).
"""

import os
import sys
import unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

try:
    from fastapi.testclient import TestClient
    from core.modes.web_api import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    TestClient = None
    app = None


class TestCozmoAPI(unittest.TestCase):
    def setUp(self):
        if not HAS_FASTAPI:
            self.skipTest("FastAPI not installed in current environment")
        self.client = TestClient(app)


    def test_cozmo_status_endpoint(self):
        """Verify GET /api/cozmo/status returns valid JSON structure."""
        resp = self.client.get("/api/cozmo/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("battery_voltage", data)
        self.assertIn("head_pitch_deg", data)
        self.assertIn("robot_pose", data)

    def test_cozmo_anchors_list_endpoint(self):
        """Verify GET /api/cozmo/anchors returns visual anchor list."""
        resp = self.client.get("/api/cozmo/anchors")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("anchors", data)
        self.assertIsInstance(data["anchors"], list)

    def test_cozmo_command_endpoint(self):
        """Verify POST /api/cozmo/command accepts commands."""
        # Tilt head
        resp = self.client.post("/api/cozmo/command", json={"action": "tilt_head", "angle_deg": 15.0})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("head_pitch_deg"), 15.0)

        # Stop
        resp = self.client.post("/api/cozmo/command", json={"action": "stop"})
        self.assertEqual(resp.status_code, 200)

    def test_camera_source_switching(self):
        """Verify POST /api/cozmo/command can toggle camera source between webcam and cozmo."""
        # Switch to webcam
        resp = self.client.post("/api/cozmo/command", json={"action": "set_camera_source", "source": "webcam"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("camera_source"), "webcam")

        # Verify status endpoint reflects webcam
        status_resp = self.client.get("/api/cozmo/status")
        self.assertEqual(status_resp.json().get("camera_source"), "webcam")

        # Switch back to cozmo
        resp = self.client.post("/api/cozmo/command", json={"action": "set_camera_source", "source": "cozmo"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("camera_source"), "cozmo")

    def test_toggle_webcam(self):
        """Verify POST /api/cozmo/command can toggle webcam hardware state."""
        # Toggle off
        resp = self.client.post("/api/cozmo/command", json={"action": "toggle_webcam", "enabled": False})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("webcam_enabled"))

        # Verify status endpoint reflects webcam disabled
        status_resp = self.client.get("/api/cozmo/status")
        self.assertFalse(status_resp.json().get("webcam_enabled"))

        # Toggle on
        resp = self.client.post("/api/cozmo/command", json={"action": "toggle_webcam", "enabled": True})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("webcam_enabled"))

        # Verify status endpoint reflects webcam enabled
        status_resp = self.client.get("/api/cozmo/status")
        self.assertTrue(status_resp.json().get("webcam_enabled"))

    def test_cozmo_offline_stream_frame(self):
        """Verify generate_mjpeg_stream yields valid offline frame when Cozmo is not connected."""
        from core.modes.cozmo_api import generate_mjpeg_stream
        gen = generate_mjpeg_stream(source="cozmo")
        frame_chunk = next(gen)
        self.assertTrue(frame_chunk.startswith(b"--frame\r\nContent-Type: image/jpeg"))
        self.assertGreater(len(frame_chunk), 500)


if __name__ == "__main__":
    unittest.main()
