"""
Unit Tests for Dynamic Visual Anchor Relocation and Transient Obstacle Tracking.
"""

import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from autonomous_cozmo.vision.anchor_store import VisualAnchorStore, VisualAnchor


class TestDynamicRelocation(unittest.TestCase):
    def setUp(self):
        self.temp_store_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../scratch/test_relocation_store.json")
        )
        os.makedirs(os.path.dirname(self.temp_store_path), exist_ok=True)
        if os.path.exists(self.temp_store_path):
            os.remove(self.temp_store_path)
        self.store = VisualAnchorStore(store_path=self.temp_store_path)

    def tearDown(self):
        if os.path.exists(self.temp_store_path):
            os.remove(self.temp_store_path)

    def test_dynamic_relocation_on_displacement(self):
        """Moving an object by > 35mm should update its coordinates smoothly without creating a duplicate."""
        dummy_vec = np.ones((384,), dtype=np.float32)
        dummy_vec /= np.linalg.norm(dummy_vec)

        # Initial anchor at (100, 100)
        self.store.save_anchor(
            label="ChargingDock",
            feature_vector=dummy_vec,
            x=100.0,
            y=100.0,
            confidence_threshold=0.75,
        )

        # Re-observe ChargingDock at (250, 200) (moved by 180mm)
        updated = self.store.update_or_relocate_anchor(
            label="ChargingDock",
            observed_x=250.0,
            observed_y=200.0,
            confidence=0.88,
            smoothing_alpha=0.70,
        )

        self.assertIsNotNone(updated)
        # Position should have shifted towards (250, 200)
        self.assertGreater(updated.estimated_x, 150.0)
        self.assertGreater(updated.estimated_y, 140.0)

        # Confirm only ONE anchor exists in the store (no duplicate ghost)
        all_anchors = self.store.list_anchors()
        self.assertEqual(len(all_anchors), 1)
        self.assertEqual(all_anchors[0].label, "ChargingDock")

    def test_transient_obstacle_registration_and_pruning(self):
        """Verify that unnamed floor obstacles can be registered, merged, and pruned."""
        # 1. Register obstacle at (80, 90)
        obs1 = self.store.register_or_update_obstacle(80.0, 90.0, confidence=0.85)
        self.assertIsNotNone(obs1)
        self.assertEqual(len(self.store.list_obstacles()), 1)

        # 2. Re-observe nearby at (84, 92) -> should merge into existing obstacle
        obs2 = self.store.register_or_update_obstacle(84.0, 92.0, confidence=0.90)
        self.assertEqual(len(self.store.list_obstacles()), 1)
        self.assertEqual(obs1.id, obs2.id)

        # 3. Register distant obstacle at (300, 400) -> should create new obstacle
        obs3 = self.store.register_or_update_obstacle(300.0, 400.0, confidence=0.80)
        self.assertEqual(len(self.store.list_obstacles()), 2)

    def test_charger_default_position_behind_cozmo(self):
        """Charger should default to exactly 10 cm (100 mm) directly behind Cozmo."""
        from autonomous_cozmo.vision.anchor_store import get_default_charger_pose, DEFAULT_CHARGER_DISTANCE_MM
        
        self.assertEqual(DEFAULT_CHARGER_DISTANCE_MM, 100.0)
        
        # 1. Robot at origin facing East (0 deg) -> Charger at (-100, 0)
        cx, cy, c_theta = get_default_charger_pose((0.0, 0.0, 0.0))
        self.assertAlmostEqual(cx, -100.0)
        self.assertAlmostEqual(cy, 0.0)
        self.assertAlmostEqual(c_theta, 180.0)

        # 2. Robot at (200, 150) facing North (90 deg) -> Charger at (200, 50)
        cx2, cy2, _ = get_default_charger_pose((200.0, 150.0, 90.0))
        self.assertAlmostEqual(cx2, 200.0)
        self.assertAlmostEqual(cy2, 50.0)

        # 3. ensure_default_charger grounds charger in store
        dummy_vec = np.zeros(384, dtype=np.float32)
        self.store.save_anchor("charger", dummy_vec, x=0.0, y=0.0)
        c_anchor = self.store.ensure_default_charger(robot_pose=(0.0, 0.0, 0.0), force=True)
        self.assertIsNotNone(c_anchor)
        self.assertAlmostEqual(c_anchor.estimated_x, -100.0)
        self.assertAlmostEqual(c_anchor.estimated_y, 0.0)

    def test_camera_spots_charger_and_relocates_map_position(self):
        """When Cozmo camera spots charger or any object, map location updates dynamically."""
        dummy_vec = np.ones((384,), dtype=np.float32)
        dummy_vec /= np.linalg.norm(dummy_vec)

        # Start with charger at default 10cm behind Cozmo (-100, 0)
        self.store.save_anchor("charger", dummy_vec, x=-100.0, y=0.0)
        self.assertEqual(self.store.get_anchor("charger").estimated_x, -100.0)

        # Camera spots charger in front at (140, 20)
        updated = self.store.update_or_relocate_anchor(
            label="charger",
            observed_x=140.0,
            observed_y=20.0,
            confidence=0.92,
            smoothing_alpha=0.75,
        )
        self.assertIsNotNone(updated)
    def test_locked_charger_does_not_relocate(self):
        """When an anchor is locked, update_or_relocate_anchor and update_anchor_pose must not alter coordinates."""
        dummy_vec = np.ones((384,), dtype=np.float32)
        dummy_vec /= np.linalg.norm(dummy_vec)

        self.store.save_anchor("charger", dummy_vec, x=250.0, y=50.0)
        self.store.lock_charger()
        self.assertTrue(self.store.is_charger_locked())

        # Vision attempts to relocate locked charger to (400, 100)
        relocated = self.store.update_or_relocate_anchor(
            label="charger",
            observed_x=400.0,
            observed_y=100.0,
            confidence=0.99,
        )
        self.assertIsNotNone(relocated)
        self.assertEqual(relocated.estimated_x, 250.0)
        self.assertEqual(relocated.estimated_y, 50.0)

        # Unlock allows relocation
        self.store.unlock_charger()
        self.assertFalse(self.store.is_charger_locked())
        relocated2 = self.store.update_or_relocate_anchor(
            label="charger",
            observed_x=400.0,
            observed_y=100.0,
            confidence=0.99,
        )
        self.assertIsNotNone(relocated2)
        self.assertGreater(relocated2.estimated_x, 300.0)


if __name__ == "__main__":
    unittest.main()
