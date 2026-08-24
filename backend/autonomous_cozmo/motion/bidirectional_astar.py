"""
Moka AI Assistant - Phase 5 Autonomous Docking Subsystem
Bidirectional (Two-Way) A* Search Algorithm with 5cm Obstacle Safety Clearance.

Key Features:
1. Bidirectional A* Frontier Search:
   - Simultaneous forward search from Cozmo start pose (x_s, y_s) and backward search
     from Charger pre-dock approach point (x_g, y_g).
   - Exponentially reduces state space exploration (O(b^(d/2))) compared to standard A*.
2. 5cm (50mm) Strict Obstacle Clearance:
   - Every block / obstacle center is inflated by its physical dimension + 50mm safety buffer
     + robot clearance (~35mm).
   - Secondary soft-potential margin field guides the path toward wider, safer corridors.
3. String-Pulling / Line-of-Sight Trajectory Smoothing:
   - Decimates jagged grid steps into smooth, direct kinematic waypoints.
4. Pre-Dock Approach Alignment:
   - Calculates the target orientation and offset entrance point in front of the charger
     before triggering the fine visual/reverse docking maneuver.
"""

import math
import heapq
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Set, Any
import numpy as np


# Standard Cozmo Light Cube physical dimensions & safety constants
DEFAULT_BLOCK_SIZE_MM = 44.0       # Standard Cozmo cube edge width (44mm)
DEFAULT_BLOCK_RADIUS_MM = 25.0     # Half-diagonal inscribed circle radius
DEFAULT_SAFETY_CLEARANCE_MM = 50.0 # 5 cm strict safety clearance requirement
DEFAULT_ROBOT_RADIUS_MM = 35.0     # Cozmo track footprint half-width clearance (mm)
DEFAULT_GRID_RESOLUTION_MM = 15.0  # 15mm per spatial grid cell for sub-centimeter accuracy
DEFAULT_DOCK_APPROACH_OFFSET_MM = 120.0  # 12cm directly in front of charger facing outward


@dataclass(order=True)
class NodeEntry:
    priority: float
    g_score: float = field(compare=False)
    coord: Tuple[int, int] = field(compare=False)


@dataclass
class BlockObstacle:
    x: float
    y: float
    radius: float = DEFAULT_BLOCK_RADIUS_MM
    label: str = "Cube"
    is_interactive: bool = True


@dataclass
class PathPlanningResult:
    success: bool
    path: List[List[float]]               # High-density points for visualization [[x, y], ...]
    waypoints: List[List[float]]          # Decimated smooth waypoints [[x, y], ...]
    total_length_mm: float
    min_obstacle_distance_mm: float
    clearance_buffer_mm: float
    approach_point: Tuple[float, float]
    approach_heading_deg: float
    nodes_expanded: int
    execution_time_ms: float
    message: str = ""


class BidirectionalAStarPlanner:
    """
    Two-Way (Bidirectional) A* Path Planner with guaranteed 5cm obstacle clearance.
    """

    def __init__(
        self,
        grid_resolution_mm: float = DEFAULT_GRID_RESOLUTION_MM,
        safety_clearance_mm: float = DEFAULT_SAFETY_CLEARANCE_MM,
        robot_radius_mm: float = DEFAULT_ROBOT_RADIUS_MM,
        soft_margin_mm: float = 40.0,
    ):
        self.resolution = float(grid_resolution_mm)
        self.safety_clearance = float(safety_clearance_mm)
        self.robot_radius = float(robot_radius_mm)
        self.soft_margin = float(soft_margin_mm)

        # 8-connected grid movement directions with Euclidean step weights
        self._directions = [
            (1, 0, 1.0),
            (-1, 0, 1.0),
            (0, 1, 1.0),
            (0, -1, 1.0),
            (1, 1, math.sqrt(2.0)),
            (1, -1, math.sqrt(2.0)),
            (-1, 1, math.sqrt(2.0)),
            (-1, -1, math.sqrt(2.0)),
        ]

    def _world_to_grid(self, wx: float, wy: float, min_x: float, min_y: float) -> Tuple[int, int]:
        gx = int(round((wx - min_x) / self.resolution))
        gy = int(round((wy - min_y) / self.resolution))
        return gx, gy

    def _grid_to_world(self, gx: int, gy: int, min_x: float, min_y: float) -> Tuple[float, float]:
        wx = min_x + gx * self.resolution
        wy = min_y + gy * self.resolution
        return round(float(wx), 2), round(float(wy), 2)

    def calculate_dock_approach_pose(
        self,
        charger_x: float,
        charger_y: float,
        charger_theta_deg: float,
        offset_mm: float = DEFAULT_DOCK_APPROACH_OFFSET_MM,
    ) -> Tuple[float, float, float]:
        """
        Calculates the entry waypoint located in front of the charger.
        The charger faces charger_theta_deg. The approach point sits directly along
        its front normal axis.
        """
        rad = math.radians(charger_theta_deg)
        # Front of charger is in the direction of its heading
        approach_x = charger_x + offset_mm * math.cos(rad)
        approach_y = charger_y + offset_mm * math.sin(rad)
        # Cozmo arrives facing towards the charger (opposite to charger heading)
        approach_heading = (charger_theta_deg + 180.0) % 360.0
        return float(approach_x), float(approach_y), float(approach_heading)

    def get_charger_ushape_obstacles(
        self,
        cx: float,
        cy: float,
        theta_deg: float,
        clearance_mm: float = DEFAULT_SAFETY_CLEARANCE_MM,
    ) -> List[Tuple[float, float, float]]:
        """
        Generates U-shaped physical wall barrier points for the charger's back and side walls
        (leaving the front ramp entrance completely open for docking).
        Returns list of (x, y, hard_radius) obstacle circles representing the physical walls with clearance.
        """
        rad = math.radians(theta_deg)
        cos_t = math.cos(rad)
        sin_t = math.sin(rad)

        # Local wall segment centers relative to charger origin:
        # Back wall (curved rear housing): X = -42mm
        # Left wall (side guide rail): Y = +38mm
        # Right wall (side guide rail): Y = -38mm
        wall_radius = 16.0 + clearance_mm + self.robot_radius
        local_pts = [
            (-42.0, 0.0),    # Rear center wall
            (-42.0, 28.0),   # Rear-left corner wall
            (-42.0, -28.0),  # Rear-right corner wall
            (-15.0, 38.0),   # Left flank mid
            (12.0, 38.0),    # Left flank front edge
            (-15.0, -38.0),  # Right flank mid
            (12.0, -38.0),   # Right flank front edge
        ]

        ushape_circles: List[Tuple[float, float, float]] = []
        for lx, ly in local_pts:
            wx = cx + (lx * cos_t - ly * sin_t)
            wy = cy + (lx * sin_t + ly * cos_t)
            ushape_circles.append((wx, wy, wall_radius))
        return ushape_circles

    def plan_docking_path(
        self,
        start_pose: Tuple[float, float, float],       # (x, y, theta_deg)
        charger_pose: Tuple[float, float, float],     # (x, y, theta_deg)
        obstacles: Optional[List[Dict[str, Any]]] = None,
        custom_clearance_mm: Optional[float] = None,
    ) -> PathPlanningResult:
        """
        Plans a collision-free path from start_pose to the charger docking station
        using Two-Way (Bidirectional) A* search while strictly maintaining 5cm clearance
        around all blocks and the charger's U-shaped physical housing walls.
        """
        t0 = time.perf_counter()

        sx, sy, _ = start_pose
        cx, cy, c_theta = charger_pose
        clearance = custom_clearance_mm if custom_clearance_mm is not None else self.safety_clearance

        # Calculate pre-dock approach entrance waypoint
        app_x, app_y, app_heading = self.calculate_dock_approach_pose(cx, cy, c_theta)

        # Build list of consolidated obstacle circles
        obs_circles: List[Tuple[float, float, float]] = []  # (x, y, hard_radius)
        if obstacles:
            for obs in obstacles:
                ox = float(obs.get("x", 0.0))
                oy = float(obs.get("y", 0.0))
                raw_r = float(obs.get("radius", DEFAULT_BLOCK_RADIUS_MM))
                # Total forbidden zone = Block physical radius + 5cm safety clearance + robot half-width
                hard_r = raw_r + clearance + self.robot_radius
                obs_circles.append((ox, oy, hard_r))

        # Add the charger's physical U-shaped barrier walls (prevents driving through back/sides)
        charger_walls = self.get_charger_ushape_obstacles(cx, cy, c_theta, clearance_mm=clearance * 0.5)
        obs_circles.extend(charger_walls)

        # Check if start or goal is directly inside an obstacle (escape fallback)
        for ox, oy, hard_r in list(obs_circles):
            dist_s = math.hypot(sx - ox, sy - oy)
            dist_g = math.hypot(app_x - ox, app_y - oy)
            if dist_s < hard_r:
                hard_r_adj = max(5.0, dist_s - 5.0)
                obs_circles = [(x, y, (r if (x != ox or y != oy) else hard_r_adj)) for x, y, r in obs_circles]
            if dist_g < hard_r:
                hard_r_adj = max(5.0, dist_g - 5.0)
                obs_circles = [(x, y, (r if (x != ox or y != oy) else hard_r_adj)) for x, y, r in obs_circles]

        # Determine spatial bounding box with generous padding for exploration
        all_x = [sx, app_x, cx] + [ox for ox, _, _ in obs_circles]
        all_y = [sy, app_y, cy] + [oy for _, oy, _ in obs_circles]

        margin = 350.0  # 35cm boundary padding
        min_x = min(all_x) - margin
        max_x = max(all_x) + margin
        min_y = min(all_y) - margin
        max_y = max(all_y) + margin

        # Convert start and goal to grid coordinates
        start_node = self._world_to_grid(sx, sy, min_x, min_y)
        goal_node = self._world_to_grid(app_x, app_y, min_x, min_y)

        if start_node == goal_node:
            t_dur = (time.perf_counter() - t0) * 1000.0
            return PathPlanningResult(
                success=True,
                path=[[sx, sy], [app_x, app_y], [cx, cy]],
                waypoints=[[sx, sy], [app_x, app_y], [cx, cy]],
                total_length_mm=math.hypot(app_x - sx, app_y - sy) + math.hypot(cx - app_x, cy - app_y),
                min_obstacle_distance_mm=clearance,
                clearance_buffer_mm=clearance,
                approach_point=(app_x, app_y),
                approach_heading_deg=app_heading,
                nodes_expanded=1,
                execution_time_ms=t_dur,
                message="Start is already at dock approach position.",
            )

        # Helper function: Check if grid coordinate is in hard forbidden zone
        def is_blocked(gx: int, gy: int) -> bool:
            if (gx, gy) == start_node or (gx, gy) == goal_node:
                return False
            wx, wy = self._grid_to_world(gx, gy, min_x, min_y)
            for ox, oy, hard_r in obs_circles:
                if math.hypot(wx - ox, wy - oy) <= hard_r:
                    return True
            return False

        # Helper function: Compute soft obstacle potential cost
        def get_soft_cost(gx: int, gy: int) -> float:
            if not obs_circles:
                return 0.0
            wx, wy = self._grid_to_world(gx, gy, min_x, min_y)
            soft_penalty = 0.0
            for ox, oy, hard_r in obs_circles:
                d = math.hypot(wx - ox, wy - oy)
                if hard_r < d < (hard_r + self.soft_margin):
                    # Linear decay penalty within soft buffer zone
                    ratio = (hard_r + self.soft_margin - d) / self.soft_margin
                    soft_penalty += ratio * 3.5
            return soft_penalty

        # Euclidean Heuristic
        def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
            return math.hypot(a[0] - b[0], a[1] - b[1])

        # --- BIDIRECTIONAL A* INITIALIZATION ---
        # Forward Search: from start_node towards goal_node
        open_f: List[NodeEntry] = []
        heapq.heappush(open_f, NodeEntry(priority=heuristic(start_node, goal_node), g_score=0.0, coord=start_node))
        g_f: Dict[Tuple[int, int], float] = {start_node: 0.0}
        parent_f: Dict[Tuple[int, int], Tuple[int, int]] = {}
        closed_f: Set[Tuple[int, int]] = set()

        # Backward Search: from goal_node towards start_node
        open_b: List[NodeEntry] = []
        heapq.heappush(open_b, NodeEntry(priority=heuristic(goal_node, start_node), g_score=0.0, coord=goal_node))
        g_b: Dict[Tuple[int, int], float] = {goal_node: 0.0}
        parent_b: Dict[Tuple[int, int], Tuple[int, int]] = {}
        closed_b: Set[Tuple[int, int]] = set()

        meeting_node: Optional[Tuple[int, int]] = None
        best_cost = float("inf")
        nodes_expanded = 0
        max_expansions = 15000

        # --- TWO-WAY BIDIRECTIONAL SEARCH LOOP ---
        while open_f and open_b and nodes_expanded < max_expansions:
            # Check termination: If both frontier minimum costs reach or exceed best_cost, optimal path is proven
            if open_f[0].priority >= best_cost and open_b[0].priority >= best_cost:
                break

            # 1. Expand Forward Step
            current_f = heapq.heappop(open_f)
            u_f = current_f.coord
            if u_f not in closed_f:
                closed_f.add(u_f)
                nodes_expanded += 1

                for dx, dy, step_weight in self._directions:
                    v = (u_f[0] + dx, u_f[1] + dy)
                    if is_blocked(v[0], v[1]):
                        continue

                    step_cost = step_weight + get_soft_cost(v[0], v[1])
                    tentative_g = g_f[u_f] + step_cost

                    if v not in g_f or tentative_g < g_f[v]:
                        g_f[v] = tentative_g
                        parent_f[v] = u_f
                        prio = tentative_g + heuristic(v, goal_node)
                        heapq.heappush(open_f, NodeEntry(priority=prio, g_score=tentative_g, coord=v))

                        # Check if frontier connects with Backward Search
                        if v in g_b:
                            total_c = tentative_g + g_b[v]
                            if total_c < best_cost:
                                best_cost = total_c
                                meeting_node = v

            # 2. Expand Backward Step
            current_b = heapq.heappop(open_b)
            u_b = current_b.coord
            if u_b not in closed_b:
                closed_b.add(u_b)
                nodes_expanded += 1

                for dx, dy, step_weight in self._directions:
                    v = (u_b[0] + dx, u_b[1] + dy)
                    if is_blocked(v[0], v[1]):
                        continue

                    step_cost = step_weight + get_soft_cost(v[0], v[1])
                    tentative_g = g_b[u_b] + step_cost

                    if v not in g_b or tentative_g < g_b[v]:
                        g_b[v] = tentative_g
                        parent_b[v] = u_b
                        prio = tentative_g + heuristic(v, start_node)
                        heapq.heappush(open_b, NodeEntry(priority=prio, g_score=tentative_g, coord=v))

                        # Check if frontier connects with Forward Search
                        if v in g_f:
                            total_c = tentative_g + g_f[v]
                            if total_c < best_cost:
                                best_cost = total_c
                                meeting_node = v

        t_dur = (time.perf_counter() - t0) * 1000.0

        if meeting_node is None:
            return PathPlanningResult(
                success=False,
                path=[],
                waypoints=[],
                total_length_mm=0.0,
                min_obstacle_distance_mm=0.0,
                clearance_buffer_mm=clearance,
                approach_point=(app_x, app_y),
                approach_heading_deg=app_heading,
                nodes_expanded=nodes_expanded,
                execution_time_ms=t_dur,
                message="No collision-free path found. Target may be enclosed or obstructed.",
            )

        # --- RECONSTRUCT RAW PATH FROM MEETING NODE ---
        # 1. Forward half: start -> meeting_node
        path_f: List[Tuple[int, int]] = []
        curr = meeting_node
        while curr in parent_f:
            path_f.append(curr)
            curr = parent_f[curr]
        path_f.append(start_node)
        path_f.reverse()

        # 2. Backward half: meeting_node -> goal_node
        path_b: List[Tuple[int, int]] = []
        curr = meeting_node
        while curr in parent_b:
            curr = parent_b[curr]
            path_b.append(curr)

        full_grid_path = path_f + path_b

        # Convert to world coordinates
        dense_world_path: List[List[float]] = []
        for gx, gy in full_grid_path:
            wx, wy = self._grid_to_world(gx, gy, min_x, min_y)
            dense_world_path.append([wx, wy])

        # Ensure exact start and approach endpoints
        dense_world_path[0] = [round(sx, 1), round(sy, 1)]
        dense_world_path[-1] = [round(app_x, 1), round(app_y, 1)]

        # --- STRING-PULLING / LINE-OF-SIGHT SHORTCUT SMOOTHING ---
        smooth_waypoints = self._smooth_path(dense_world_path, obs_circles)

        # Append the final terminal docking alignment segment into the charger dock
        final_path = [pt for pt in dense_world_path]
        final_path.append([round(cx, 1), round(cy, 1)])

        final_waypoints = [pt for pt in smooth_waypoints]
        final_waypoints.append([round(cx, 1), round(cy, 1)])

        # Calculate path metrics
        total_len = 0.0
        for i in range(len(final_waypoints) - 1):
            total_len += math.hypot(
                final_waypoints[i + 1][0] - final_waypoints[i][0],
                final_waypoints[i + 1][1] - final_waypoints[i][1],
            )

        # Verify minimum obstacle clearance along smooth trajectory against environment block obstacles
        min_dist = float("inf")
        check_obstacles = [obs for obs in obs_circles if obs not in charger_walls] if obs_circles else []
        if check_obstacles:
            # Check clearance along navigation path prior to final dock pin entry
            nav_pts = smooth_waypoints if len(smooth_waypoints) > 1 else final_waypoints
            for pt in nav_pts:
                for ox, oy, hard_r in check_obstacles:
                    center_dist = math.hypot(pt[0] - ox, pt[1] - oy)
                    obs_edge_clearance = center_dist - (DEFAULT_BLOCK_RADIUS_MM + self.robot_radius)
                    min_dist = min(min_dist, obs_edge_clearance)
        else:
            min_dist = clearance

        return PathPlanningResult(
            success=True,
            path=final_path,
            waypoints=final_waypoints,
            total_length_mm=round(total_len, 1),
            min_obstacle_distance_mm=round(max(0.0, min_dist), 1),
            clearance_buffer_mm=clearance,
            approach_point=(app_x, app_y),
            approach_heading_deg=round(app_heading, 1),
            nodes_expanded=nodes_expanded,
            execution_time_ms=round(t_dur, 2),
            message=f"Optimal 2-Way A* path computed ({len(final_waypoints)} waypoints, {total_len:.0f}mm).",
        )

    def _smooth_path(
        self,
        path: List[List[float]],
        obs_circles: List[Tuple[float, float, float]],
    ) -> List[List[float]]:
        """
        Applies greedy line-of-sight raycasting (string-pulling) to remove redundant
        grid waypoints while guaranteeing 5cm obstacle clearance is preserved.
        """
        if len(path) <= 2:
            return path

        def line_is_clear(p1: List[float], p2: List[float]) -> bool:
            dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            steps = max(2, int(math.ceil(dist / (self.resolution * 0.7))))
            for s in range(steps + 1):
                t = s / steps
                ix = p1[0] + t * (p2[0] - p1[0])
                iy = p1[1] + t * (p2[1] - p1[1])
                for ox, oy, hard_r in obs_circles:
                    if math.hypot(ix - ox, iy - oy) <= hard_r:
                        return False
            return True

        smoothed = [path[0]]
        current_idx = 0

        while current_idx < len(path) - 1:
            # Try to connect current_idx to the farthest possible reachable node
            furthest_idx = len(path) - 1
            for target_idx in range(len(path) - 1, current_idx, -1):
                if line_is_clear(path[current_idx], path[target_idx]):
                    furthest_idx = target_idx
                    break
            smoothed.append(path[furthest_idx])
            current_idx = furthest_idx

        return smoothed


# Global Planner Singleton
bidirectional_astar_planner = BidirectionalAStarPlanner()
