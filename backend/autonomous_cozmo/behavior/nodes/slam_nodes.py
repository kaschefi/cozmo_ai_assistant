from typing import Optional
from autonomous_cozmo.behavior.tree import Node, NodeStatus, Blackboard
from autonomous_cozmo.vision.landmark_slam import landmark_slam


class CheckVisibleAnchorCondition(Node):
    """
    Condition Node:
    Queries LandmarkSLAM to check if a high-confidence environmental anchor is visible in camera FOV.
    """
    def __init__(self, name: str = "CheckVisibleAnchor", landmark_name: str = "ChargingDock"):
        super().__init__(name)
        self.landmark_name = landmark_name

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        is_visible, azimuth, dist = landmark_slam.check_landmark_visibility(self.landmark_name)
        if is_visible:
            blackboard.set("visible_anchor", {
                "name": self.landmark_name,
                "azimuth": azimuth,
                "distance": dist,
            })
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        else:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE


class ExecuteSLAMOffsetCorrectionAction(Node):
    """
    Action Node:
    Executes visual odometry drift correction when an anchor is confirmed in view.
    """
    def __init__(self, name: str = "ExecuteSLAMOffsetCorrection"):
        super().__init__(name)

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        anchor_data = blackboard.get("visible_anchor")
        if not anchor_data:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

        res = landmark_slam.correct_drift_from_observation(
            landmark_name=anchor_data["name"],
            observed_azimuth_deg=anchor_data["azimuth"],
            observed_distance_mm=anchor_data["distance"],
        )

        blackboard.set("last_slam_correction", res)
        blackboard.set("visible_anchor", None)
        self.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS
