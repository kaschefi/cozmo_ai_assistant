import math
import threading
from typing import Tuple, Dict, Any


class PoseTracker:
    """
    Tracks Cozmo's estimated 2D desk-relative pose (x, y, heading) and head pitch,
    supporting dynamic coordinate updates/offsets from host vision (e.g. SLAM / REMIND)
    to mitigate track-slippage odometry drift.
    """

    def __init__(self, x: float = 0.0, y: float = 0.0, theta_deg: float = 0.0):
        self._lock = threading.Lock()
        self.x = float(x)
        self.y = float(y)
        self.theta = math.radians(theta_deg)
        self.head_pitch_rad = 0.0

        # Host dynamic drift offsets
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.offset_theta = 0.0

    def update_pose(self, x: float, y: float, theta_deg: float):
        """Directly sets raw estimated pose."""
        with self._lock:
            self.x = float(x)
            self.y = float(y)
            self.theta = math.radians(theta_deg)

    def update_relative_motion(self, dist_mm: float, turn_deg: float):
        """Updates internal pose by integrating relative forward motion and rotation."""
        with self._lock:
            self.theta += math.radians(turn_deg)
            # Normalize theta to [-pi, pi]
            self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
            self.x += dist_mm * math.cos(self.theta)
            self.y += dist_mm * math.sin(self.theta)

    def update_offset(self, dx: float, dy: float, dtheta_deg: float):
        """
        Applies dynamic coordinate corrections/offsets from external visual SLAM or host vision
        to compensate for desk odometry drift.
        """
        with self._lock:
            self.offset_x += float(dx)
            self.offset_y += float(dy)
            self.offset_theta += math.radians(dtheta_deg)

    def reset_pose(self, x: float = 0.0, y: float = 0.0, theta_deg: float = 0.0):
        """Resets pose and clears offsets."""
        with self._lock:
            self.x = float(x)
            self.y = float(y)
            self.theta = math.radians(theta_deg)
            self.offset_x = 0.0
            self.offset_y = 0.0
            self.offset_theta = 0.0

    def get_effective_pose(self) -> Tuple[float, float, float]:
        """Returns the drift-corrected effective pose (eff_x, eff_y, eff_theta_deg)."""
        with self._lock:
            eff_x = self.x + self.offset_x
            eff_y = self.y + self.offset_y
            eff_theta = math.degrees(self.theta + self.offset_theta)
            return eff_x, eff_y, eff_theta

    def get_pose(self) -> Dict[str, float]:
        """Returns complete pose state dictionary."""
        eff_x, eff_y, eff_theta_deg = self.get_effective_pose()
        with self._lock:
            return {
                "x": self.x,
                "y": self.y,
                "theta_deg": math.degrees(self.theta),
                "offset_x": self.offset_x,
                "offset_y": self.offset_y,
                "offset_theta_deg": math.degrees(self.offset_theta),
                "effective_x": eff_x,
                "effective_y": eff_y,
                "effective_theta_deg": eff_theta_deg,
                "head_pitch_deg": math.degrees(self.head_pitch_rad),
            }


# Global singleton PoseTracker for desk motion tracking
pose_tracker = PoseTracker()
