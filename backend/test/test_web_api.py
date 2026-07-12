import os
import sys

# Ensure both workspace root and backend directory are in the Python search path
# so that imports resolve correctly when run directly
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(TEST_DIR)
WORKSPACE_DIR = os.path.dirname(BACKEND_DIR)

if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Import the app to test
from core.modes.web_api import app

class TestWebAPISecurity(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Store original environment variable
        self.original_token = os.environ.get("MOKA_ADMIN_TOKEN")

    def tearDown(self):
        # Restore environment variable
        if self.original_token is not None:
            os.environ["MOKA_ADMIN_TOKEN"] = self.original_token
        elif "MOKA_ADMIN_TOKEN" in os.environ:
            del os.environ["MOKA_ADMIN_TOKEN"]

    def test_health_endpoint_is_public(self):
        # The health endpoint should remain public and not require X-Moka-Token
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "connected": True})

    @patch("core.modes.web_api.process_user_intent", new_callable=AsyncMock)
    def test_chat_endpoint_success_with_valid_token(self, mock_process):
        # Setup expected token
        os.environ["MOKA_ADMIN_TOKEN"] = "test-secret-token"
        mock_process.return_value = "Hello user"
        
        response = self.client.post(
            "/api/chat",
            headers={"X-Moka-Token": "test-secret-token"},
            json={"message": "hello", "session_id": "test_session"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["response"], "Hello user")
        mock_process.assert_called_once_with("hello", session_id="test_session")

    def test_chat_endpoint_forbidden_with_invalid_token(self):
        os.environ["MOKA_ADMIN_TOKEN"] = "test-secret-token"
        
        response = self.client.post(
            "/api/chat",
            headers={"X-Moka-Token": "wrong-token"},
            json={"message": "hello", "session_id": "test_session"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Forbidden", response.json()["detail"])

    def test_chat_endpoint_forbidden_with_missing_token_header(self):
        os.environ["MOKA_ADMIN_TOKEN"] = "test-secret-token"
        
        response = self.client.post(
            "/api/chat",
            json={"message": "hello", "session_id": "test_session"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Forbidden", response.json()["detail"])

    def test_chat_endpoint_rejects_all_when_token_unconfigured(self):
        # Remove variable from environment
        if "MOKA_ADMIN_TOKEN" in os.environ:
            del os.environ["MOKA_ADMIN_TOKEN"]
            
        response = self.client.post(
            "/api/chat",
            headers={"X-Moka-Token": "some-token"},
            json={"message": "hello", "session_id": "test_session"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("unconfigured", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
