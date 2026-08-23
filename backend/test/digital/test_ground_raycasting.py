"""
Unit Tests for Inverse Perspective Ground Contact Raycasting (Pinhole Ground Plane z=0).
"""

import math
import unittest
import numpy as np

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from autonomous_cozmo.vision.anchor_store import estimate_ground_position


class TestGroundRaycasting(unittest.TestCase):
    def test_forward_raycasting_horizontal(self):
        """Test forward distance when head pitch is horizontal (0 rad) with bottom of object at y=0.85."""
        bbox_norm = (0.2, 0.4, 0.85, 0.6)  # Centered horizontally, bottom at 0.85
        robot_pose = (0.0, 0.0, 0.0)
        head_angle = 0.0

        wx, wy, dist = estimate_ground_position(
            bbox_norm=bbox_norm,
            robot_pose=robot_pose,
            head_angle_rad=head_angle,
            cam_height_mm=45.0,
        )

        # Distance should be positive, in physical mm range
        self.assertGreater(wx, 35.0)
        self.assertLess(wx, 500.0)
        # Lateral offset should be very close to 0 (centered)
        self.assertAlmostEqual(wy, 0.0, delta=15.0)
        self.assertGreater(dist, 35.0)

    def test_robot_heading_transformation(self):
        """Verify that when robot is rotated 90 degrees, forward distance translates into global Y."""
        bbox_norm = (0.2, 0.4, 0.85, 0.6)
        robot_pose = (100.0, 50.0, 90.0)  # at (100, 50) facing North (+Y)
        head_angle = 0.15

        wx, wy, dist = estimate_ground_position(
            bbox_norm=bbox_norm,
            robot_pose=robot_pose,
            head_angle_rad=head_angle,
        )

        # X should stay near 100mm, Y should be 50mm + forward distance
        self.assertAlmostEqual(wx, 100.0, delta=20.0)
        self.assertGreater(wy, 50.0 + 35.0)

    def test_tilt_down_distance_reduction(self):
        """Tilting the head downwards (negative pitch) should reduce the calculated ground distance for the same pixel."""
        bbox_norm = (0.3, 0.4, 0.8, 0.6)
        robot_pose = (0.0, 0.0, 0.0)

        wx_shallow, _, _ = estimate_ground_position(bbox_norm, robot_pose, head_angle_rad=0.0)
        wx_steep, _, _ = estimate_ground_position(bbox_norm, robot_pose, head_angle_rad=-0.15)

        self.assertGreater(wx_shallow, wx_steep, "Steeper downwards head angle should produce shorter forward distance")


if __name__ == "__main__":
    unittest.main()

