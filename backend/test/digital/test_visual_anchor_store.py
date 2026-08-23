"""
Unit Test Suite for VisualAnchorStore & Semantic Object Grounding (visual_anchors.json).
Verifies anchor persistence, JSON serialization, cosine similarity re-identification, and REMIND integration.
"""

import sys
import os
import unittest
import tempfile
import numpy as np
from PIL import Image

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from autonomous_cozmo.vision import (
    VisualAnchor,
    VisualAnchorStore,
    REMINDMemoryEngine,
)


class TestVisualAnchorStore(unittest.TestCase):

    def setUp(self):
        # Create a temporary file for isolated test persistence
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_path = os.path.join(self.temp_dir.name, "test_visual_anchors.json")
        self.store = VisualAnchorStore(store_path=self.store_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load_anchors(self):
        """Verify saving anchors persists to JSON and loads back cleanly."""
        feat1 = np.random.randn(384).astype(np.float32)
        feat1 /= np.linalg.norm(feat1)

        # Save ChargingDock
        anchor1 = self.store.save_anchor(
            label="ChargingDock",
            feature_vector=feat1,
            x=0.0,
            y=0.0,
            theta_deg=180.0,
            is_permanent=True,
            notes="Permanent Home Base",
        )
        self.assertEqual(anchor1.label, "ChargingDock")
        self.assertTrue(os.path.exists(self.store_path))

        # Re-instantiate store from the same file to verify persistence
        new_store = VisualAnchorStore(store_path=self.store_path)
        loaded = new_store.load_anchors()
        self.assertIn("ChargingDock", loaded)
        loaded_dock = loaded["ChargingDock"]
        self.assertEqual(loaded_dock.estimated_x, 0.0)
        self.assertEqual(loaded_dock.estimated_theta_deg, 180.0)
        self.assertTrue(loaded_dock.is_permanent)

        # Verify vector similarity
        sim = float(np.dot(feat1, loaded_dock.get_numpy_vector()))
        self.assertAlmostEqual(sim, 1.0, places=4)

    def test_cosine_similarity_identification(self):
        """Verify exact and noisy feature vector re-identification."""
        # 1. Base vector for Coffee Mug
        mug_feat = np.zeros(384, dtype=np.float32)
        mug_feat[10:20] = 1.0
        mug_feat /= np.linalg.norm(mug_feat)

        # 2. Base vector for Charger
        charger_feat = np.zeros(384, dtype=np.float32)
        charger_feat[50:60] = 1.0
        charger_feat /= np.linalg.norm(charger_feat)

        self.store.save_anchor("CoffeeMug", mug_feat, x=100.0, y=50.0)
        self.store.save_anchor("ChargingDock", charger_feat, x=0.0, y=0.0)

        # Test exact match
        label, sim, anchor = self.store.identify(mug_feat)
        self.assertEqual(label, "CoffeeMug")
        self.assertGreater(sim, 0.99)
        self.assertIsNotNone(anchor)

        # Test slightly noisy match (e.g. angle change)
        noisy_mug = mug_feat + 0.02 * np.random.randn(384).astype(np.float32)
        noisy_mug /= np.linalg.norm(noisy_mug)
        label_noisy, sim_noisy, _ = self.store.identify(noisy_mug, min_similarity=0.70)
        self.assertEqual(label_noisy, "CoffeeMug")
        self.assertGreater(sim_noisy, 0.70)


        # Test un-enrolled / novel object
        novel_feat = np.zeros(384, dtype=np.float32)
        novel_feat[100:110] = 1.0
        novel_feat /= np.linalg.norm(novel_feat)
        novel_label, novel_sim, novel_anchor = self.store.identify(novel_feat, min_similarity=0.72)
        self.assertIsNone(novel_label)
        self.assertIsNone(novel_anchor)

    def test_update_and_delete_anchor(self):
        """Verify updating coordinates and deleting an anchor."""
        feat = np.random.randn(384).astype(np.float32)
        feat /= np.linalg.norm(feat)

        self.store.save_anchor("RubiksCube", feat, x=120.0, y=-40.0)
        self.assertEqual(self.store.get_anchor("RubiksCube").estimated_x, 120.0)

        # Update pose
        self.store.update_anchor_pose("RubiksCube", new_x=175.0, new_y=-10.0, new_theta_deg=45.0)
        updated = self.store.get_anchor("RubiksCube")
        self.assertEqual(updated.estimated_x, 175.0)
        self.assertEqual(updated.estimated_y, -10.0)
        self.assertEqual(updated.estimated_theta_deg, 45.0)

        # Delete
        self.assertTrue(self.store.delete_anchor("RubiksCube"))
        self.assertIsNone(self.store.get_anchor("RubiksCube"))

    def test_remind_engine_integration(self):
        """Verify REMINDMemoryEngine loads saved anchors and recognizes them in process_feature."""
        feat = np.zeros(384, dtype=np.float32)
        feat[42] = 1.0
        self.store.save_anchor("ChargingDock", feat, x=0.0, y=0.0)

        # Instantiate REMIND with our test store
        remind = REMINDMemoryEngine(anchor_store=self.store)
        self.assertIn("anchor_chargingdock", remind.memory_bank)

        # Process observation matching ChargingDock
        nov, matched_id, sim = remind.process_feature(
            feature_vector=feat,
            curr_x=0.0,
            curr_y=0.0,
            curr_theta_deg=0.0,
            explicit_target_x=5.0,
            explicit_target_y=-2.0,
        )

        self.assertEqual(matched_id, "anchor_chargingdock")
        self.assertGreater(sim, 0.99)
        self.assertLess(nov, 0.05)

        # Verify teach_anchor method
        new_feat = np.zeros(384, dtype=np.float32)
        new_feat[88] = 1.0
        remind.teach_anchor("DeskLamp", new_feat, x=200.0, y=100.0)
        self.assertIn("anchor_desklamp", remind.memory_bank)
        self.assertIsNotNone(self.store.get_anchor("DeskLamp"))

        remind.shutdown()

    def test_spatial_patch_object_detection(self):
        """Verify detect_objects_in_patches localizes matching spatial patch clusters and ignores empty scenes."""
        # 1. Create a 16x16 patch grid (256 patches)
        grid_h, grid_w = 16, 16
        background_tokens = np.random.randn(grid_h, grid_w, 384).astype(np.float32)
        background_tokens /= np.linalg.norm(background_tokens, axis=-1, keepdims=True)

        # 2. Plant a "ChargingDock" object in top-left (patches 2:6, 2:6)
        dock_feat = np.zeros(384, dtype=np.float32)
        dock_feat[100:110] = 1.0
        dock_feat /= np.linalg.norm(dock_feat)
        self.store.save_anchor("ChargingDock", dock_feat, x=0.0, y=0.0)

        # 3. Plant a "CoffeeMug" object in bottom-right (patches 10:14, 10:14)
        mug_feat = np.zeros(384, dtype=np.float32)
        mug_feat[200:210] = 1.0
        mug_feat /= np.linalg.norm(mug_feat)
        self.store.save_anchor("CoffeeMug", mug_feat, x=150.0, y=80.0)

        # Put features into patch grid
        background_tokens[2:6, 2:6, :] = dock_feat
        background_tokens[10:14, 10:14, :] = mug_feat

        # Test detection
        dets = self.store.detect_objects_in_patches(background_tokens, min_patch_similarity=0.80, min_matching_patches=4)
        self.assertEqual(len(dets), 2)
        labels = [d["label"] for d in dets]
        self.assertIn("ChargingDock", labels)
        self.assertIn("CoffeeMug", labels)

        # Test empty scene (when objects leave the camera view)
        empty_scene = np.random.randn(grid_h, grid_w, 384).astype(np.float32)
        empty_scene /= np.linalg.norm(empty_scene, axis=-1, keepdims=True)
        empty_dets = self.store.detect_objects_in_patches(empty_scene, min_patch_similarity=0.80, min_matching_patches=2)
        self.assertEqual(len(empty_dets), 0)


if __name__ == "__main__":
    unittest.main()

