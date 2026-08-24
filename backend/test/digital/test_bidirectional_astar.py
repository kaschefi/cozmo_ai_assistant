import os
import sys
import math
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from autonomous_cozmo.motion.bidirectional_astar import (
    BidirectionalAStarPlanner,
    bidirectional_astar_planner,
    DEFAULT_SAFETY_CLEARANCE_MM,
    DEFAULT_BLOCK_RADIUS_MM,
    DEFAULT_ROBOT_RADIUS_MM,
)


class TestBidirectionalAStar(unittest.TestCase):
    """Test suite for Bidirectional A* path planner and obstacle clearance."""

    def test_direct_line_of_sight_docking_path(self):
        """When no obstacles exist, planner should produce direct path to dock approach point."""
        planner = BidirectionalAStarPlanner(grid_resolution_mm=10.0, safety_clearance_mm=50.0)
        start_pose = (0.0, 0.0, 0.0)
        charger_pose = (300.0, 0.0, 180.0)  # Charger at (300, 0) facing -X (180 deg)

        res = planner.plan_docking_path(
            start_pose=start_pose,
            charger_pose=charger_pose,
            obstacles=[],
        )

        self.assertTrue(res.success)
        self.assertGreaterEqual(len(res.waypoints), 2)
        # Start point matches
        self.assertAlmostEqual(res.waypoints[0][0], 0.0, delta=5.0)
        self.assertAlmostEqual(res.waypoints[0][1], 0.0, delta=5.0)
        # End point matches charger coordinates
        self.assertAlmostEqual(res.waypoints[-1][0], 300.0, delta=5.0)
        self.assertAlmostEqual(res.waypoints[-1][1], 0.0, delta=5.0)
        # Pre-dock approach point should be in front of charger
        self.assertLess(res.approach_point[0], 300.0)
        self.assertLess(res.execution_time_ms, 50.0)

    def test_strict_5cm_block_clearance_guarantee(self):
        """
        Place a block directly between Cozmo and the Charger.
        Verify that the computed path goes around the block and maintains >= 50mm clearance.
        """
        planner = BidirectionalAStarPlanner(grid_resolution_mm=10.0, safety_clearance_mm=50.0)
        start_pose = (0.0, 0.0, 0.0)
        charger_pose = (450.0, 0.0, 180.0)  # Approach point is at (330, 0)

        # Block placed directly in the center path at (160, 0)
        block_x, block_y = 160.0, 0.0
        block_radius = 25.0
        obstacles = [{"x": block_x, "y": block_y, "radius": block_radius, "label": "Cube 1"}]

        res = planner.plan_docking_path(
            start_pose=start_pose,
            charger_pose=charger_pose,
            obstacles=obstacles,
            custom_clearance_mm=50.0,
        )

        self.assertTrue(res.success)
        self.assertGreaterEqual(len(res.waypoints), 3)

        min_center_dist = float("inf")
        # Check every point along the dense path
        for pt in res.path:
            dist_to_center = math.hypot(pt[0] - block_x, pt[1] - block_y)
            min_center_dist = min(min_center_dist, dist_to_center)

        # Distance from block center to robot center must be >= 25mm + 50mm + 35mm = 110mm (with grid tolerance)
        self.assertGreaterEqual(
            min_center_dist,
            block_radius + 50.0 + DEFAULT_ROBOT_RADIUS_MM - 15.0,
            f"Path came too close to block! Min center distance: {min_center_dist:.1f}mm"
        )
        self.assertGreaterEqual(res.min_obstacle_distance_mm, 45.0)

    def test_multi_block_corridor_navigation(self):
        """
        Test slalom / corridor navigation through multiple blocks (Cube 1, Cube 2, Cube 3).
        """
        planner = BidirectionalAStarPlanner(grid_resolution_mm=15.0, safety_clearance_mm=50.0)
        start_pose = (0.0, 0.0, 0.0)
        charger_pose = (500.0, 0.0, 180.0)

        blocks = [
            {"x": 150.0, "y": 30.0, "radius": 25.0, "label": "Cube 1"},
            {"x": 250.0, "y": -40.0, "radius": 25.0, "label": "Cube 2"},
            {"x": 350.0, "y": 20.0, "radius": 25.0, "label": "Cube 3"},
        ]

        res = planner.plan_docking_path(
            start_pose=start_pose,
            charger_pose=charger_pose,
            obstacles=blocks,
            custom_clearance_mm=50.0,
        )

        self.assertTrue(res.success)
        self.assertGreater(res.total_length_mm, 500.0)
        self.assertGreater(res.nodes_expanded, 0)

    def test_approach_orientation_and_reverse_vector(self):
        """
        Verify that the approach point and heading angle correctly orient Cozmo
        to face the front of the charger before docking.
        """
        planner = BidirectionalAStarPlanner()
        # Charger at (100, 200) facing 90 degrees (+Y)
        charger_x, charger_y, charger_theta = 100.0, 200.0, 90.0
        app_x, app_y, app_heading = planner.calculate_dock_approach_pose(
            charger_x, charger_y, charger_theta, offset_mm=120.0
        )

        # Front is at +Y (200 + 120 = 320)
        self.assertAlmostEqual(app_x, 100.0, delta=1.0)
        self.assertAlmostEqual(app_y, 320.0, delta=1.0)
        # Approach heading to drive into dock facing -Y (270 deg)
        self.assertAlmostEqual(app_heading, 270.0, delta=1.0)

    def test_performance_sub_35ms(self):
        """Bidirectional A* should converge in under 35ms on standard desk environments."""
        start_pose = (-150.0, -100.0, 45.0)
        charger_pose = (350.0, 200.0, 225.0)
        blocks = [
            {"x": 50.0, "y": 50.0, "radius": 25.0, "label": "Cube 1"},
            {"x": -50.0, "y": 100.0, "radius": 25.0, "label": "Cube 2"},
        ]

        res = bidirectional_astar_planner.plan_docking_path(
            start_pose=start_pose,
            charger_pose=charger_pose,
            obstacles=blocks,
            custom_clearance_mm=50.0,
        )

        self.assertTrue(res.success)
        self.assertLess(res.execution_time_ms, 35.0)

    def test_charger_ushape_barrier_prevents_rear_entry(self):
        """
        When starting behind the charger (e.g. X = -500, Y = 0), the path MUST NOT cut
        through the charger's back or side walls; it must navigate around the U-shape to the front entrance.
        """
        start_pose = (-500.0, 0.0, 0.0)
        charger_pose = (-300.0, 0.0, 0.0)

        res = bidirectional_astar_planner.plan_docking_path(
            start_pose=start_pose,
            charger_pose=charger_pose,
            custom_clearance_mm=50.0,
        )

        self.assertTrue(res.success)
        # Approach point must be in front of the charger (+X from -300 -> -180)
        self.assertAlmostEqual(res.approach_point[0], -180.0, delta=2.0)

        # Path must deviate sideways (around Y) and not drive through charger center (-300, 0)
        max_lateral_dev = max(abs(pt[1]) for pt in res.path)
        self.assertGreater(max_lateral_dev, 40.0, "Path must go around the U-shape wall flank!")


if __name__ == "__main__":
    unittest.main()
