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


if __name__ == "__main__":
    unittest.main()
