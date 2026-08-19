import math
import threading
from typing import Dict, Optional, Tuple, Any

from autonomous_cozmo.motion.pose_tracker import pose_tracker

# Terminal formatting colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


class LandmarkSLAM:
    """
    Visual Landmark Local SLAM Loop.
    Maintains persistent environmental anchors (e.g., Charging Dock at (0, 0), Monitor Stand).
    When Cozmo spots an anchor via camera, compares expected odometry against visual observation
    and calls pose_tracker.update_offset(dx, dy, dtheta) to completely eliminate desk track-slip drift.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Dictionary of registered ground-truth landmarks: name -> {'x': mm, 'y': mm, 'theta_deg': deg}
        self.known_landmarks: Dict[str, Dict[str, float]] = {
            "ChargingDock": {"x": 0.0, "y": 0.0, "theta_deg": 0.0},
            "MonitorStand": {"x": 160.0, "y": 0.0, "theta_deg": 0.0},
        }

    def register_landmark(self, name: str, x: float, y: float, theta_deg: float = 0.0):
        """Registers or updates ground-truth coordinates of a persistent environmental landmark."""
        with self._lock:
            self.known_landmarks[name] = {
                "x": float(x),
                "y": float(y),
                "theta_deg": float(theta_deg),
            }

    def get_landmark(self, name: str) -> Optional[Dict[str, float]]:
        with self._lock:
            return self.known_landmarks.get(name)

    def check_landmark_visibility(
        self,
        landmark_name: str,
        fov_deg: float = 60.0,
        max_range_mm: float = 300.0,
    ) -> Tuple[bool, float, float]:
        """
        Determines if a landmark is theoretically within Cozmo's current camera Field-Of-View.
        Returns: (is_visible, relative_azimuth_deg, distance_mm)
        """
        lm = self.get_landmark(landmark_name)
        if not lm:
            return False, 0.0, 0.0

        curr_x, curr_y, curr_theta = pose_tracker.get_effective_pose()
        dx = lm["x"] - curr_x
        dy = lm["y"] - curr_y
        dist = math.hypot(dx, dy)

        if dist > max_range_mm or dist < 10.0:
            return False, 0.0, dist

        # Calculate bearing angle to landmark
        angle_to_lm_deg = math.degrees(math.atan2(dy, dx))
        rel_azimuth = (angle_to_lm_deg - curr_theta + 180.0) % 360.0 - 180.0

        is_in_fov = abs(rel_azimuth) <= (fov_deg / 2.0)
        return is_in_fov, rel_azimuth, dist

    def correct_drift_from_observation(
        self,
        landmark_name: str,
        observed_azimuth_deg: float,
        observed_distance_mm: float,
        observed_heading_delta_deg: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Calculates the discrepancy between estimated pose and visual landmark observation,
        and applies dynamic offset correction to PoseTracker.

        :param landmark_name: Ground-truth landmark identifier.
        :param observed_azimuth_deg: Angle of landmark relative to camera center (+left, -right).
        :param observed_distance_mm: Optical distance to landmark in mm.
        :param observed_heading_delta_deg: Optical orientation error of the landmark marker if available.
        """
        lm = self.get_landmark(landmark_name)
        if not lm:
            return {"status": "error", "message": f"Unknown landmark {landmark_name}"}

        with self._lock:
            eff_x, eff_y, eff_theta = pose_tracker.get_effective_pose()

            # Global ray angle from robot to landmark
            global_bearing_deg = (eff_theta + observed_azimuth_deg) % 360.0
            global_bearing_rad = math.radians(global_bearing_deg)

            # Ground truth robot location calculated from landmark:
            # P_robot = P_landmark - (dist * [cos(ray), sin(ray)])
            true_robot_x = lm["x"] - observed_distance_mm * math.cos(global_bearing_rad)
            true_robot_y = lm["y"] - observed_distance_mm * math.sin(global_bearing_rad)

            # Calculate drift errors
            dx = true_robot_x - eff_x
            dy = true_robot_y - eff_y
            dtheta = observed_heading_delta_deg

            # Apply correction offset to PoseTracker
            pose_tracker.update_offset(dx, dy, dtheta)

            new_x, new_y, new_theta = pose_tracker.get_effective_pose()

            print(f"{CYAN}[Landmark SLAM] Anchor '{landmark_name}' recognized! Correcting odometry drift: dx={dx:+.1f}mm, dy={dy:+.1f}mm, dtheta={dtheta:+.1f}°{RESET}")
            print(f"  -> Drift Corrected Pose: ({new_x:.1f}, {new_y:.1f}, {new_theta:.1f}°)")

            return {
                "status": "success",
                "landmark": landmark_name,
                "drift_offset": (dx, dy, dtheta),
                "corrected_pose": (new_x, new_y, new_theta),
            }


# Global singleton LandmarkSLAM
landmark_slam = LandmarkSLAM()
