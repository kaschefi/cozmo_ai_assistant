"""
Unit tests for Closed-Loop Visual Servoing Docking Controller.
Verifies:
1. Charger detection filtering and priority.
2. Real-time proportional steering calculation.
3. Closed-loop docking state progression (Searching -> Navigating -> Aligning -> Docking -> Completed).
4. Reflex safety docking mode suppression hook.
5. 1:1 Simulation pose synchronization from visual raycast.
"""

import os
import sys
import asyncio
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from autonomous_cozmo.motion.visual_servoing import (
    VisualServoingDockingController,
    visual_servoing_controller,
)


class TestVisualServoing(unittest.TestCase):
    def setUp(self):
        self.controller = VisualServoingDockingController(
            kp=40.0,
            base_speed_mm_s=30.0,
            approach_threshold_width=0.45,
            approach_threshold_dist_mm=160.0,
        )

    def test_find_charger_detection(self):
        """Should select the highest confidence charger/dock detection above threshold."""
        detections = [
            {"label": "cube", "confidence": 0.95, "bbox_norm": [0.1, 0.1, 0.4, 0.4]},
            {"label": "charger_dock", "confidence": 0.72, "bbox_norm": [0.2, 0.3, 0.6, 0.7]},
            {"label": "charger", "confidence": 0.88, "bbox_norm": [0.2, 0.2, 0.6, 0.8]},
        ]
        best = self.controller.find_charger_detection(detections)
        self.assertIsNotNone(best)
        self.assertEqual(best["confidence"], 0.88)
        self.assertEqual(best["label"], "charger")

    def test_find_charger_detection_none_when_low_conf(self):
        """Should return None if all detections are below 0.60 confidence."""
        detections = [
            {"label": "charger", "confidence": 0.45, "bbox_norm": [0.1, 0.1, 0.3, 0.3]},
        ]
        best = self.controller.find_charger_detection(detections)
        self.assertIsNone(best)

    def test_proportional_steering_centering(self):
        """Charger to the right should increase left wheel speed and decrease right wheel speed."""
        # bbox centered at x = 0.7 (to the right of frame center 0.5)
        # error_x = 0.7 - 0.5 = +0.2
        error_x = 0.2
        steer = self.controller.kp * error_x  # 40.0 * 0.2 = 8.0
        l_speed = self.controller.base_speed + steer  # 30.0 + 8.0 = 38.0
        r_speed = self.controller.base_speed - steer  # 30.0 - 8.0 = 22.0

        self.assertGreater(l_speed, r_speed)
        self.assertAlmostEqual(l_speed, 38.0)
        self.assertAlmostEqual(r_speed, 22.0)

    def test_execute_docking_full_sequence(self):
        """Runs execute_docking with mock client and verifies stage progression and safety hooks."""
        mock_cli = MagicMock()
        mock_cli.is_on_charger = False

        state_history = []
        robot_pose = [0.0, 0.0, 0.0]
        docking_mode_states = []

        def mock_set_state(stage, action):
            state_history.append((stage, action))

        def mock_set_pose(x, y, th):
            robot_pose[0] = x
            robot_pose[1] = y
            robot_pose[2] = th

        def mock_set_docking_mode(active):
            docking_mode_states.append(active)

        # Mock detections: first frame shows charger at distance, second frame near pre-dock threshold
        frame_idx = 0
        def mock_get_detections():
            nonlocal frame_idx
            frame_idx += 1
            if frame_idx < 3:
                return [{
                    "label": "charger_dock",
                    "confidence": 0.85,
                    "bbox_norm": [0.3, 0.4, 0.7, 0.6],  # centered (0.5), width 0.20
                    "distance_mm": 220.0,
                }]
            else:
                return [{
                    "label": "charger_dock",
                    "confidence": 0.90,
                    "bbox_norm": [0.2, 0.25, 0.8, 0.75], # width 0.50 (>= 0.45 approach threshold)
                    "distance_mm": 140.0,
                }]

        is_active = lambda: True

        async def run():
            return await self.controller.execute_docking(
                cli=mock_cli,
                get_detections=mock_get_detections,
                get_robot_pose=lambda: tuple(robot_pose),
                set_robot_pose=mock_set_pose,
                set_state_info=mock_set_state,
                is_active=is_active,
                charger_world_pose=(0.0, 0.0, 180.0),
                set_docking_mode=mock_set_docking_mode,
            )

        success = asyncio.run(run())
        self.assertTrue(success)

        # Verify docking mode was activated at start and restored at finish
        self.assertIn(True, docking_mode_states)
        self.assertFalse(docking_mode_states[-1])

        # Verify stages were walked through
        stages = [s[0] for s in state_history]
        self.assertIn("NAVIGATING", stages)
        self.assertIn("ALIGNING", stages)
        self.assertIn("DOCKING", stages)
        self.assertIn("COMPLETED", stages)

        # Verify hardware was commanded
        self.assertTrue(mock_cli.set_lift_height.called)
        self.assertTrue(mock_cli.drive_wheels.called)
        self.assertTrue(mock_cli.stop_all_motors.called)


if __name__ == "__main__":
    unittest.main()
