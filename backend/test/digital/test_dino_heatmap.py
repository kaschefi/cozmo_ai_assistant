"""
Unit & Integration Test Suite for DINO Heatmap and Cozmo Vision Perception Engine.
Verifies DINOPrecisionExtractor, DINOHeatmapVisualizer, enhance_cozmo_frame, and render_cozmo_frame_heatmap.
"""

import sys
import os
import unittest
import numpy as np
from PIL import Image
import cv2

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from autonomous_cozmo.vision import (
    DINOPrecisionExtractor,
    DINOHeatmapVisualizer,
    enhance_cozmo_frame,
    render_cozmo_frame_heatmap,
    dino_heatmap_extractor,
    dino_heatmap_visualizer,
    DEFAULT_COZMO_CAM_PARAMS,
    REMINDMemoryEngine,
)


class TestDINOHeatmapEngine(unittest.TestCase):

    def test_imports_and_singletons(self):
        """Verify module exports and global singletons are properly instantiated."""
        self.assertIsNotNone(dino_heatmap_extractor)
        self.assertIsNotNone(dino_heatmap_visualizer)
        self.assertIn("red_gain", DEFAULT_COZMO_CAM_PARAMS)
        self.assertIn("blue_gain", DEFAULT_COZMO_CAM_PARAMS)

    def test_enhance_cozmo_frame(self):
        """Verify camera color balance and exposure correction pipeline."""
        dummy_frame = np.full((120, 160, 3), 128, dtype=np.uint8)
        enhanced = enhance_cozmo_frame(dummy_frame)
        self.assertEqual(enhanced.shape, (120, 160, 3))
        self.assertEqual(enhanced.dtype, np.uint8)

    def test_precision_extractor_calibration_and_inference(self):
        """Verify calibration accumulation, master PCA calculation, and feature extraction."""
        extractor = DINOPrecisionExtractor(backend="dinov3", calibration_frames=3, lazy_init=True)
        
        # Test calibration frames
        for i in range(3):
            test_img = Image.new("RGB", (224, 224), color=(i * 40, i * 60, i * 80))
            feat, mask = extractor.extract(test_img, is_calibrating=True)
            self.assertEqual(feat.shape, (384,))
            self.assertEqual(len(feat), 384)
            self.assertEqual(mask.dtype, np.uint8)

        # Test inference frame
        test_infer = Image.new("RGB", (224, 224), color=(100, 150, 200))
        feat, mask = extractor.extract(test_infer, is_calibrating=False)
        self.assertEqual(feat.shape, (384,))
        self.assertEqual(len(mask.shape), 3)
        self.assertEqual(mask.shape[2], 3)
        self.assertEqual(mask.dtype, np.uint8)

        # Test recalibration
        extractor.recalibrate()
        self.assertIsNone(extractor.master_eigenvectors)
        self.assertEqual(len(extractor.calibration_pool), 0)

    def test_heatmap_visualizer_modes(self):
        """Verify HUD and composite rendering across all view modes."""
        viz = DINOHeatmapVisualizer(default_view_mode=DINOHeatmapVisualizer.VIEW_DUAL)
        frame_bgr = np.full((240, 320, 3), 100, dtype=np.uint8)
        patch_rgb = np.full((14, 14, 3), 200, dtype=np.uint8)

        # 1. Dual-View Mode
        dual_comp = viz.render_composite(
            frame_bgr=frame_bgr,
            patch_color_rgb=patch_rgb,
            view_mode=DINOHeatmapVisualizer.VIEW_DUAL,
            novelty_score=0.75,
            classification="NOVEL OBJECT",
            active_memories=5,
            frame_count=42,
        )
        self.assertEqual(dual_comp.shape, (240, 640, 3))  # Left (320) + Right (320) = 640

        # 2. Blended Mode
        blended_comp = viz.render_composite(
            frame_bgr=frame_bgr,
            patch_color_rgb=patch_rgb,
            view_mode=DINOHeatmapVisualizer.VIEW_BLENDED,
            novelty_score=0.20,
            classification="FAMILIAR ANCHOR",
        )
        self.assertEqual(blended_comp.shape, (240, 320, 3))

        # 3. Heatmap-Only Mode
        heat_comp = viz.render_composite(
            frame_bgr=frame_bgr,
            patch_color_rgb=patch_rgb,
            view_mode=DINOHeatmapVisualizer.VIEW_HEATMAP_ONLY,
        )
        self.assertEqual(heat_comp.shape, (240, 320, 3))

        # 4. Clean Feed Mode
        clean_comp = viz.render_composite(
            frame_bgr=frame_bgr,
            patch_color_rgb=patch_rgb,
            view_mode=DINOHeatmapVisualizer.VIEW_CLEAN_FEED,
        )
        self.assertEqual(clean_comp.shape, (240, 320, 3))

        # 5. Alert Overlay Mode
        alert_comp = viz.render_composite(
            frame_bgr=frame_bgr,
            patch_color_rgb=patch_rgb,
            alert_text="CLIFF DETECTED",
        )
        self.assertIsNotNone(alert_comp)

        # 6. Mode Cycling
        curr_mode = viz.view_mode
        next_mode = viz.cycle_view_mode()
        self.assertEqual(next_mode, (curr_mode + 1) % len(viz.VIEW_MODE_NAMES))

    def test_render_cozmo_frame_heatmap_pipeline(self):
        """Verify end-to-end one-call pipeline with REMIND memory integration."""
        extractor = DINOPrecisionExtractor(backend="dinov3", calibration_frames=2, lazy_init=True)
        remind = REMINDMemoryEngine(novelty_threshold=0.35)
        raw_img = Image.new("RGB", (320, 240), color=(120, 140, 160))

        # Calibration step
        comp1, mask1, telem1 = render_cozmo_frame_heatmap(
            raw_frame=raw_img,
            extractor=extractor,
            remind_engine=remind,
            is_calibrating=True,
            frame_count=1,
        )
        self.assertEqual(telem1["is_calibrating"], True)
        self.assertIsNotNone(comp1)

        # Inference step
        comp2, mask2, telem2 = render_cozmo_frame_heatmap(
            raw_frame=raw_img,
            extractor=extractor,
            remind_engine=remind,
            is_calibrating=False,
            frame_count=2,
        )
        self.assertEqual(telem2["is_calibrating"], False)
        self.assertIn("latency_ms", telem2)
        self.assertIn("novelty", telem2)
        self.assertIn("classification", telem2)
        remind.shutdown()

    def test_remind_automatic_heatmap_worker(self):
        """Verify that REMIND async frame worker automatically computes and caches the heatmap."""
        remind = REMINDMemoryEngine(novelty_threshold=0.35)
        raw_img = Image.new("RGB", (160, 120), color=(180, 90, 45))

        # Enqueue frame asynchronously
        remind.process_frame_async(raw_img, (10.0, 20.0, 0.0))

        # Wait for worker thread to process (allow up to 15s for CPU model load)
        import time
        for _ in range(60):
            comp, mask, telem = remind.get_latest_view()
            if comp is not None:
                break
            time.sleep(0.2)


        comp, mask, telem = remind.get_latest_view()
        self.assertIsNotNone(comp, "Expected composite frame to be automatically cached by REMIND worker")
        self.assertIsNotNone(mask, "Expected patch heatmap mask to be automatically cached by REMIND worker")
        self.assertIn("novelty", telem)
        self.assertIn("latency_ms", telem)

        remind.shutdown()

    def test_extract_from_click_segment_and_bbox(self):
        """Verify interactive mouse click object segmentation and custom bounding box extraction."""
        extractor = DINOPrecisionExtractor()
        test_img = Image.new("RGB", (224, 224), color=(0, 200, 100))

        # 1. Click segment test
        feat, bbox, mask, obj_mask = extractor.extract_from_click_segment(
            test_img,
            click_norm_x=0.5,
            click_norm_y=0.5,
            sim_threshold=0.75,
        )
        self.assertEqual(feat.shape, (384,))
        self.assertAlmostEqual(float(np.linalg.norm(feat)), 1.0, places=3)
        self.assertEqual(len(bbox), 4)
        self.assertTrue(0.0 <= bbox[0] <= bbox[2] <= 1.0)
        self.assertTrue(0.0 <= bbox[1] <= bbox[3] <= 1.0)

        # 2. Custom BBox extraction test
        custom_box = (0.2, 0.3, 0.7, 0.8)
        bbox_feat, bbox_mask, dense_tokens = extractor.extract_from_bbox(test_img, bbox_norm=custom_box)
        self.assertEqual(bbox_feat.shape, (384,))
        self.assertAlmostEqual(float(np.linalg.norm(bbox_feat)), 1.0, places=3)


if __name__ == "__main__":
    unittest.main()


