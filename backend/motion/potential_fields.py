import math
from typing import List, Dict, Tuple, Optional


def compute_attractive_force(
    curr_x: float,
    curr_y: float,
    target_x: float,
    target_y: float,
) -> Tuple[float, float, float]:
    """
    Computes normalized attractive vector pointing toward the target and distance.
    Returns (att_x, att_y, distance_mm).
    """
    dx = target_x - curr_x
    dy = target_y - curr_y
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return 0.0, 0.0, 0.0
    return dx / dist, dy / dist, dist


def compute_obstacle_repulsion(
    curr_x: float,
    curr_y: float,
    obstacles: Optional[List[Dict[str, float]]] = None,
    k_rep: float = 150.0,
    safety_margin_mm: float = 120.0,
) -> Tuple[float, float]:
    """
    Computes artificial potential field repulsive vector from a list of static obstacles.
    Each obstacle is a dict: {'x': float, 'y': float, 'radius': float}
    
    Returns (rep_x, rep_y).
    """
    if not obstacles:
        return 0.0, 0.0

    rep_x = 0.0
    rep_y = 0.0

    for obs in obstacles:
        ox = float(obs.get("x", 0.0))
        oy = float(obs.get("y", 0.0))
        radius = float(obs.get("radius", 30.0))
        influence_r = radius + safety_margin_mm

        obs_dx = curr_x - ox
        obs_dy = curr_y - oy
        obs_dist = math.hypot(obs_dx, obs_dy)

        # Apply inverse-square repulsive force within influence radius
        if 0.001 < obs_dist < influence_r:
            rep_factor = k_rep * ((1.0 / obs_dist) - (1.0 / influence_r)) / (obs_dist ** 2)
            rep_x += (obs_dx / obs_dist) * rep_factor
            rep_y += (obs_dy / obs_dist) * rep_factor

    return rep_x, rep_y


def compute_apf_heading(
    curr_x: float,
    curr_y: float,
    target_x: float,
    target_y: float,
    obstacles: Optional[List[Dict[str, float]]] = None,
    k_rep: float = 150.0,
    safety_margin_mm: float = 120.0,
) -> Tuple[float, float]:
    """
    Calculates the resultant desired heading (degrees in [-180, 180]) and distance to target
    by summing attractive and repulsive forces.
    
    Returns (desired_heading_deg, distance_to_target_mm).
    """
    att_x, att_y, dist = compute_attractive_force(curr_x, curr_y, target_x, target_y)
    if dist < 1e-6:
        return 0.0, 0.0

    rep_x, rep_y = compute_obstacle_repulsion(
        curr_x=curr_x,
        curr_y=curr_y,
        obstacles=obstacles,
        k_rep=k_rep,
        safety_margin_mm=safety_margin_mm,
    )

    net_x = att_x + rep_x
    net_y = att_y + rep_y

    desired_heading_rad = math.atan2(net_y, net_x)
    desired_heading_deg = math.degrees(desired_heading_rad)
    return desired_heading_deg, dist
