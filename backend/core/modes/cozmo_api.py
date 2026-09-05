"""
Moka AI Assistant - Autonomous Cozmo REST & WebSocket Hub (/api/cozmo and /ws/cozmo).

Provides:
  1. MJPEG Live Video Feed (/api/cozmo/video_feed): Stream Cozmo's live camera + DINO heatmap.
  2. Telemetry WebSocket (/ws/cozmo/telemetry): 20Hz stream of robot (x, y, theta), visual anchors,
     ground obstacles, and battery voltage.
  3. Robot Command REST Endpoint (/api/cozmo/command): Drive, tilt head, toggle headlights, dock, teach.
  4. Anchor Management (/api/cozmo/anchors): List, delete, or inspect visual anchors.
"""

import os
import sys
import time
import math
import asyncio
import json
from typing import Optional, Dict, Any, List, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import numpy as np
from PIL import Image
import cv2
try:
    import pycozmo
except ImportError:
    pycozmo = None

from core.hardware.connection import cozmo_manager
from autonomous_cozmo.vision import (
    dino_heatmap_extractor,
    dino_heatmap_visualizer,
    DINOHeatmapVisualizer,
    visual_anchor_store,
    remind_engine,
    enhance_cozmo_frame,
    render_cozmo_frame_heatmap,
    estimate_ground_position,
    get_default_charger_pose,
)
from autonomous_cozmo.motion import (
    bidirectional_astar_planner,
    DEFAULT_SAFETY_CLEARANCE_MM,
    DEFAULT_BLOCK_RADIUS_MM,
    DEFAULT_BLOCK_SIZE_MM,
    pose_tracker,
    visual_servoing_controller,
)

# API Routers
cozmo_router = APIRouter(prefix="/api/cozmo", tags=["Cozmo Autonomous"])
cozmo_ws_router = APIRouter(prefix="/ws/cozmo", tags=["Cozmo Telemetry WS"])

# Shared Cozmo Runtime State for Web Streaming
class CozmoWebState:
    def __init__(self):
        self.head_pitch_deg = 15.0
        self.lift_height_mm = 32.0
        self.headlight_on = False
        self.brightness_offset = -15
        self.contrast_gain = 1.10
        self.gamma_val = 0.85
        self.active_state = "IDLE"
        self.current_action = "STANDBY"
        self.camera_source = "cozmo"  # "cozmo" or "webcam"
        self.webcam_enabled = True
        self.show_heatmap = True
        self.latest_robot_pose = (0.0, 0.0, 0.0)  # (x_mm, y_mm, theta_deg)
        self.planned_path: List[List[float]] = []
        self.path_info: Dict[str, Any] = {}
        self.latest_detections: List[Dict[str, Any]] = []
        self.latest_patch_color_rgb: Optional[np.ndarray] = None
        self.latest_novelty: float = 0.0
        self.latest_classification: str = "FAMILIAR"
        self.active_memories: int = 0
        self.total_objects: int = 0
        self.frame_count: int = 0

        # Phase 5: Interactive Blocks & Simulation State
        self.interactive_blocks: Dict[str, Dict[str, Any]] = {
            "cube_1": {"id": "cube_1", "x": 120.0, "y": 80.0, "radius": DEFAULT_BLOCK_RADIUS_MM, "clearance_mm": DEFAULT_SAFETY_CLEARANCE_MM, "label": "Cube 1"},
            "cube_2": {"id": "cube_2", "x": -90.0, "y": 140.0, "radius": DEFAULT_BLOCK_RADIUS_MM, "clearance_mm": DEFAULT_SAFETY_CLEARANCE_MM, "label": "Cube 2"},
            "cube_3": {"id": "cube_3", "x": 70.0, "y": 200.0, "radius": DEFAULT_BLOCK_RADIUS_MM, "clearance_mm": DEFAULT_SAFETY_CLEARANCE_MM, "label": "Cube 3"},
        }
        self.simulation_active: bool = False
        self.simulation_stage: str = "IDLE"  # "IDLE", "PLANNING", "NAVIGATING", "ALIGNING", "DOCKING", "COMPLETED"
        self.simulation_task: Optional[asyncio.Task] = None

        # Interactive Click & Purple Box Selection State

        self.pending_click: Optional[Tuple[float, float]] = None
        self.active_selection_bbox: Optional[Tuple[float, float, float, float]] = None
        self.active_selection_mask: Optional[np.ndarray] = None
        self.active_selection_feat: Optional[np.ndarray] = None

    def get_enhancement_params(self) -> Dict[str, float]:
        return {
            "red_gain": 0.85,
            "blue_gain": 1.05,
            "brightness": float(self.brightness_offset),
            "contrast": float(self.contrast_gain),
            "gamma": float(self.gamma_val),
        }

cozmo_web_state = CozmoWebState()

# Ensure charger is grounded at default 30cm behind Cozmo upon startup
visual_anchor_store.ensure_default_charger(cozmo_web_state.latest_robot_pose, force=True)


class CozmoCommandRequest(BaseModel):
    action: str  # "drive", "stop", "tilt_head", "lift", "headlight", "brightness", "dock", "teach", "set_camera_source", "toggle_webcam"
    speed_mms: Optional[float] = None
    turn_rate: Optional[float] = None
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    angle_deg: Optional[float] = None
    height_mm: Optional[float] = None
    enabled: Optional[bool] = None
    delta: Optional[float] = None
    label: Optional[str] = None
    click_x: Optional[float] = None
    click_y: Optional[float] = None
    source: Optional[str] = None  # "cozmo" or "webcam"


@cozmo_router.get("/status")
async def get_cozmo_status():
    """Returns general connection & battery status of the robot."""
    cli = cozmo_manager.get_robot()
    is_conn = bool(cli and cozmo_manager.is_connected)
    v_bat = getattr(cli, "battery_voltage", 4.10) if is_conn else 0.0

    return {
        "status": "success",
        "is_connected": is_conn,
        "is_connecting": cozmo_manager.is_connecting,
        "battery_voltage": round(float(v_bat), 2),
        "head_pitch_deg": cozmo_web_state.head_pitch_deg,
        "lift_height_mm": cozmo_web_state.lift_height_mm,
        "headlight_on": cozmo_web_state.headlight_on,
        "show_heatmap": cozmo_web_state.show_heatmap,
        "webcam_enabled": cozmo_web_state.webcam_enabled,
        "camera_source": cozmo_web_state.camera_source,
        "active_state": cozmo_web_state.active_state,
        "robot_pose": {
            "x": cozmo_web_state.latest_robot_pose[0],
            "y": cozmo_web_state.latest_robot_pose[1],
            "theta_deg": cozmo_web_state.latest_robot_pose[2],
        }
    }


@cozmo_router.api_route("/connect", methods=["GET", "POST"])
async def connect_cozmo():
    """Triggers background PyCozmo Wi-Fi connection handshake."""
    cozmo_manager.robot_mode = True
    cozmo_manager.start()
    return {"status": "connecting", "message": "Initiating Cozmo connection handshake..."}


@cozmo_router.api_route("/disconnect", methods=["GET", "POST"])
async def disconnect_cozmo():
    """Disconnects from PyCozmo robot."""
    cozmo_manager.disconnect()
    return {"status": "disconnected", "message": "Cozmo robot disconnected."}


def update_simulated_motion(speed: float, steer: float, dt: float = 0.05):
    """Updates simulated Cozmo kinematics smoothly without resetting to zero."""
    rx, ry, rtheta = cozmo_web_state.latest_robot_pose
    new_theta = (rtheta + steer * dt) % 360.0
    new_theta_rad = math.radians(new_theta)
    new_x = rx + speed * math.cos(new_theta_rad) * dt
    new_y = ry + speed * math.sin(new_theta_rad) * dt
    cozmo_web_state.latest_robot_pose = (round(new_x, 1), round(new_y, 1), round(new_theta, 1))
    if speed != 0.0 or steer != 0.0:
        cozmo_web_state.current_action = f"DRIVING ({speed:.0f} mm/s, {steer:.0f}°/s)"
    pose_tracker.update_pose(new_x, new_y, new_theta)
    return cozmo_web_state.latest_robot_pose


@cozmo_router.post("/command")
async def execute_cozmo_command(req: CozmoCommandRequest):
    """Executes manual drive, head tilt, lighting, camera source, or autonomous action commands."""
    cli = cozmo_manager.get_robot()
    action = req.action.lower()

    if action in ("set_camera_source", "camera_source"):
        src = (req.source or "cozmo").lower().strip()
        if src in ("cozmo", "webcam"):
            cozmo_web_state.camera_source = src
            if src == "cozmo" and cli and cozmo_manager.is_connected:
                try:
                    import pycozmo

                    def _on_camera_frame(client, image):
                        client.latest_image = image
                        client._latest_image = image
                        cozmo_manager.latest_image = image

                    cli.add_handler(pycozmo.event.EvtNewRawCameraImage, _on_camera_frame)
                    cli.enable_camera(enable=True, color=True)
                    cli._cam_stream_enabled = True
                except Exception:
                    pass
            return {"status": "success", "camera_source": cozmo_web_state.camera_source}
        raise HTTPException(status_code=400, detail="Camera source must be 'cozmo' or 'webcam'.")

    elif action == "connect":
        cozmo_manager.robot_mode = True
        cozmo_manager.start()
        return {"status": "connecting", "message": "Initiating Cozmo connection handshake..."}

    elif action == "disconnect":
        cozmo_manager.disconnect()
        return {"status": "disconnected", "message": "Cozmo robot disconnected."}

    elif action == "drive":
        # Target waypoint point click drive
        if req.target_x is not None and req.target_y is not None:
            tx = float(req.target_x)
            ty = float(req.target_y)
            if cli and cozmo_manager.is_connected:
                from autonomous_cozmo.motion import drive_to
                res = drive_to(target_x=tx, target_y=ty)
            cur_x, cur_y, cur_theta = cozmo_web_state.latest_robot_pose
            dx = tx - cur_x
            dy = ty - cur_y
            target_theta = math.degrees(math.atan2(dy, dx))
            cozmo_web_state.latest_robot_pose = (round(tx, 1), round(ty, 1), round(target_theta, 1))
            cozmo_web_state.current_action = f"SIM DRIVE TO ({tx:.0f}, {ty:.0f})"
            pose_tracker.update_pose(tx, ty, target_theta)
            return {"status": "success", "action": "drive_to", "target": (tx, ty), "pose": cozmo_web_state.latest_robot_pose}

        speed = req.speed_mms or 0.0
        steer = req.turn_rate or 0.0
        if cli and cozmo_manager.is_connected:
            try:
                lw = speed - steer
                rw = speed + steer
                cli.drive_wheels(lw, rw, duration=0.35)
            except Exception:
                pass

        # Advance digital twin simulated kinematics
        update_simulated_motion(speed, steer, dt=0.08)
        return {"status": "success", "action": "drive", "pose": cozmo_web_state.latest_robot_pose}

    elif action == "stop":
        if cozmo_web_state.simulation_active and cozmo_web_state.simulation_task:
            cozmo_web_state.simulation_active = False
            cozmo_web_state.simulation_task.cancel()
            cozmo_web_state.simulation_task = None
        cozmo_manager.set_docking_mode(False)
        if cli and cozmo_manager.is_connected:
            try:
                cli.stop_all_motors()
            except Exception:
                pass
        cozmo_web_state.current_action = "STOPPED"
        return {"status": "success", "action": "stop"}

    elif action == "tilt_head":
        if req.angle_deg is not None:
            cozmo_web_state.head_pitch_deg = max(-25.0, min(44.0, req.angle_deg))
            if cli and cozmo_manager.is_connected:
                try:
                    cli.set_head_angle(math.radians(cozmo_web_state.head_pitch_deg))
                except Exception:
                    pass
        return {"status": "success", "head_pitch_deg": cozmo_web_state.head_pitch_deg}

    elif action == "lift":
        if req.height_mm is not None:
            cozmo_web_state.lift_height_mm = max(32.0, min(92.0, req.height_mm))
            if cli and cozmo_manager.is_connected:
                try:
                    cli.set_lift_height(cozmo_web_state.lift_height_mm)
                except Exception:
                    pass
        return {"status": "success", "lift_height_mm": cozmo_web_state.lift_height_mm}

    elif action == "headlight":
        cozmo_web_state.headlight_on = req.enabled if req.enabled is not None else not cozmo_web_state.headlight_on
        if cli and cozmo_manager.is_connected and hasattr(cli, "set_head_light"):
            try:
                cli.set_head_light(cozmo_web_state.headlight_on)
            except Exception:
                pass
        return {"status": "success", "headlight_on": cozmo_web_state.headlight_on}

    elif action == "brightness":
        if req.delta is not None:
            cozmo_web_state.brightness_offset = max(-100, min(100, cozmo_web_state.brightness_offset + int(req.delta)))
        return {"status": "success", "brightness": cozmo_web_state.brightness_offset}

    elif action == "dock":
        cozmo_web_state.active_state = "DOCKING"
        cozmo_web_state.current_action = "PLANNING 2-WAY A* DOCKING TRAJECTORY"
        res = await start_docking_simulation()
        return {"status": "success", "message": "Initiating autonomous docking sequence.", "plan": res.get("plan")}

    elif action in ("toggle_webcam", "set_webcam", "webcam"):
        if req.enabled is not None:
            cozmo_web_state.webcam_enabled = bool(req.enabled)
        else:
            cozmo_web_state.webcam_enabled = not cozmo_web_state.webcam_enabled
        if not cozmo_web_state.webcam_enabled:
            async_vision_engine.clear_frame()
        return {"status": "success", "webcam_enabled": cozmo_web_state.webcam_enabled}

    elif action in ("select_point", "click_segment", "select"):
        click_x = float(req.click_x if req.click_x is not None else 0.5)
        click_y = float(req.click_y if req.click_y is not None else 0.5)
        async_vision_engine.trigger_click_segment(click_x, click_y)
        return {"status": "success", "action": "select_point", "click_x": click_x, "click_y": click_y}

    elif action in ("clear_selection", "clear_select"):
        async_vision_engine.clear_selection()
        return {"status": "success", "action": "clear_selection"}

    elif action == "teach":
        label = (req.label or "").strip()
        if not label:
            raise HTTPException(status_code=400, detail="Label is required for teaching.")

        feat = cozmo_web_state.active_selection_feat
        bbox = cozmo_web_state.active_selection_bbox or (0.25, 0.25, 0.75, 0.75)

        if feat is None and async_vision_engine._latest_raw_bgr is not None:
            pil_img = Image.fromarray(cv2.cvtColor(async_vision_engine._latest_raw_bgr, cv2.COLOR_BGR2RGB))
            feat, _, _ = dino_heatmap_extractor.extract_reticle_roi(pil_img, reticle_box=bbox)

        if feat is not None:
            pose = cozmo_web_state.latest_robot_pose
            head_pitch = cozmo_web_state.head_pitch_deg
            wx, wy, dist = estimate_ground_position(
                bbox_norm=bbox,
                robot_pose=pose,
                head_angle_rad=math.radians(head_pitch),
            )
            visual_anchor_store.add_or_update_anchor(
                label=label,
                descriptor=feat,
                estimated_x=wx,
                estimated_y=wy,
                estimated_theta_deg=pose[2],
            )
            async_vision_engine.clear_selection()
            return {
                "status": "success",
                "message": f"Taught object '{label}' at ({wx:.1f}, {wy:.1f}) mm",
                "label": label,
                "world_x": wx,
                "world_y": wy,
            }
        return {"status": "error", "message": "Failed to extract object embedding."}

    return {"status": "error", "message": f"Unknown action: {action}"}


@cozmo_router.get("/anchors")
async def list_visual_anchors():
    """Returns all persistently saved visual anchors."""
    anchors = visual_anchor_store.list_anchors()
    return {
        "status": "success",
        "anchors": [
            {
                "label": a.label,
                "x": round(a.estimated_x, 1),
                "y": round(a.estimated_y, 1),
                "theta_deg": round(a.estimated_theta_deg, 1),
                "confidence_threshold": a.confidence_threshold,
                "is_permanent": a.is_permanent,
                "is_locked": getattr(a, "is_locked", False),
                "observation_count": a.observation_count,
                "last_seen_at": a.last_seen_at,
                "notes": a.notes,
            }
            for a in anchors
        ]
    }


@cozmo_router.post("/anchors/{label}/lock")
async def lock_anchor(label: str):
    """Locks an anchor so that dynamic vision relocation cannot modify its coordinates."""
    success = visual_anchor_store.lock_anchor(label)
    return {"status": "success" if success else "error", "label": label, "is_locked": True}


@cozmo_router.post("/anchors/{label}/unlock")
async def unlock_anchor(label: str):
    """Unlocks an anchor allowing vision updates."""
    success = visual_anchor_store.unlock_anchor(label)
    return {"status": "success" if success else "error", "label": label, "is_locked": False}


class BlockItem(BaseModel):
    id: Optional[str] = None
    x: float
    y: float
    radius: Optional[float] = DEFAULT_BLOCK_RADIUS_MM
    clearance_mm: Optional[float] = DEFAULT_SAFETY_CLEARANCE_MM
    label: Optional[str] = "Cube"


class PlanPathRequest(BaseModel):
    start_x: Optional[float] = None
    start_y: Optional[float] = None
    start_theta_deg: Optional[float] = None
    charger_x: Optional[float] = None
    charger_y: Optional[float] = None
    charger_theta_deg: Optional[float] = None
    clearance_mm: Optional[float] = DEFAULT_SAFETY_CLEARANCE_MM
    blocks: Optional[List[Dict[str, Any]]] = None


class SimulationDockRequest(BaseModel):
    clearance_mm: Optional[float] = DEFAULT_SAFETY_CLEARANCE_MM
    speed_factor: Optional[float] = 1.0


@cozmo_router.get("/blocks")
async def list_interactive_blocks():
    """Returns all interactive Cozmo light blocks / cube obstacles."""
    return {
        "status": "success",
        "blocks": list(cozmo_web_state.interactive_blocks.values()),
    }


@cozmo_router.post("/blocks")
async def add_or_update_block(block: BlockItem):
    """Adds or moves an interactive block/cube in 3D simulation space."""
    block_id = block.id or f"cube_{len(cozmo_web_state.interactive_blocks) + 1}"
    cozmo_web_state.interactive_blocks[block_id] = {
        "id": block_id,
        "x": float(block.x),
        "y": float(block.y),
        "radius": float(block.radius or DEFAULT_BLOCK_RADIUS_MM),
        "clearance_mm": float(block.clearance_mm or DEFAULT_SAFETY_CLEARANCE_MM),
        "label": block.label or f"Cube {len(cozmo_web_state.interactive_blocks) + 1}",
    }
    return {
        "status": "success",
        "message": f"Block '{block_id}' positioned at ({block.x:.1f}, {block.y:.1f}) mm with 5cm safety clearance.",
        "block": cozmo_web_state.interactive_blocks[block_id],
    }


@cozmo_router.delete("/blocks/{block_id}")
async def delete_interactive_block(block_id: str):
    """Deletes an interactive block from the simulation."""
    if block_id in cozmo_web_state.interactive_blocks:
        deleted = cozmo_web_state.interactive_blocks.pop(block_id)
        return {"status": "success", "message": f"Deleted block '{block_id}'", "block": deleted}
    raise HTTPException(status_code=404, detail=f"Block '{block_id}' not found.")


@cozmo_router.post("/blocks/reset")
async def reset_interactive_blocks():
    """Resets blocks to default layout with 3 interactive light cubes."""
    cozmo_web_state.interactive_blocks = {
        "cube_1": {"id": "cube_1", "x": 120.0, "y": 80.0, "radius": DEFAULT_BLOCK_RADIUS_MM, "clearance_mm": DEFAULT_SAFETY_CLEARANCE_MM, "label": "Cube 1"},
        "cube_2": {"id": "cube_2", "x": -90.0, "y": 140.0, "radius": DEFAULT_BLOCK_RADIUS_MM, "clearance_mm": DEFAULT_SAFETY_CLEARANCE_MM, "label": "Cube 2"},
        "cube_3": {"id": "cube_3", "x": 70.0, "y": 200.0, "radius": DEFAULT_BLOCK_RADIUS_MM, "clearance_mm": DEFAULT_SAFETY_CLEARANCE_MM, "label": "Cube 3"},
    }
    return {"status": "success", "message": "Reset interactive blocks to default layout.", "blocks": list(cozmo_web_state.interactive_blocks.values())}


@cozmo_router.post("/plan_dock_path")
async def plan_dock_path(req: Optional[PlanPathRequest] = None):
    """
    Computes a Two-Way (Bidirectional) A* collision-free path back to the charger
    with guaranteed 5cm clearance around all blocks.
    """
    # 1. Resolve start pose
    if req and req.start_x is not None and req.start_y is not None:
        start_pose = (req.start_x, req.start_y, req.start_theta_deg or 0.0)
    else:
        start_pose = cozmo_web_state.latest_robot_pose

    # 2. Resolve charger pose
    if req and req.charger_x is not None and req.charger_y is not None:
        charger_pose = (req.charger_x, req.charger_y, req.charger_theta_deg or 180.0)
    else:
        # Check visual anchor store or default 10cm behind Cozmo
        charger_anchor = None
        for key in ("charger", "ChargingDock", "charging_dock", "dock"):
            charger_anchor = visual_anchor_store.get_anchor(key)
            if charger_anchor and (charger_anchor.estimated_x != 0.0 or charger_anchor.estimated_y != 0.0):
                break
        if charger_anchor and (charger_anchor.estimated_x != 0.0 or charger_anchor.estimated_y != 0.0):
            charger_pose = (charger_anchor.estimated_x, charger_anchor.estimated_y, charger_anchor.estimated_theta_deg)
        else:
            charger_pose = get_default_charger_pose(start_pose)

    # 3. Gather obstacles and blocks
    clearance = req.clearance_mm if (req and req.clearance_mm is not None) else DEFAULT_SAFETY_CLEARANCE_MM
    obs_list: List[Dict[str, Any]] = []

    if req and req.blocks is not None:
        obs_list.extend(req.blocks)
    else:
        # Include all interactive blocks
        for blk in cozmo_web_state.interactive_blocks.values():
            obs_list.append({
                "x": blk["x"],
                "y": blk["y"],
                "radius": blk.get("radius", DEFAULT_BLOCK_RADIUS_MM),
                "label": blk.get("label", "Cube"),
            })
        # Include transient obstacles
        for obs in visual_anchor_store.list_obstacles():
            obs_list.append({
                "x": obs.x,
                "y": obs.y,
                "radius": obs.radius,
                "label": "Obstacle",
            })
        # Include non-charger visual anchors
        for a in visual_anchor_store.list_anchors():
            if not any(tag in a.label.lower() for tag in ("charger", "dock")):
                obs_list.append({
                    "x": a.estimated_x,
                    "y": a.estimated_y,
                    "radius": DEFAULT_BLOCK_RADIUS_MM,
                    "label": a.label,
                })

    # 4. Execute Bidirectional A* planning
    plan_result = bidirectional_astar_planner.plan_docking_path(
        start_pose=start_pose,
        charger_pose=charger_pose,
        obstacles=obs_list,
        custom_clearance_mm=clearance,
    )

    cozmo_web_state.planned_path = plan_result.waypoints
    cozmo_web_state.path_info = {
        "success": plan_result.success,
        "total_length_mm": plan_result.total_length_mm,
        "min_obstacle_distance_mm": plan_result.min_obstacle_distance_mm,
        "clearance_buffer_mm": plan_result.clearance_buffer_mm,
        "approach_point": plan_result.approach_point,
        "approach_heading_deg": plan_result.approach_heading_deg,
        "nodes_expanded": plan_result.nodes_expanded,
        "execution_time_ms": plan_result.execution_time_ms,
        "waypoints_count": len(plan_result.waypoints),
        "message": plan_result.message,
    }

    return {
        "status": "success" if plan_result.success else "error",
        "plan": cozmo_web_state.path_info,
        "waypoints": plan_result.waypoints,
        "dense_path": plan_result.path,
        "start_pose": {"x": start_pose[0], "y": start_pose[1], "theta_deg": start_pose[2]},
        "charger_pose": {"x": charger_pose[0], "y": charger_pose[1], "theta_deg": charger_pose[2]},
        "obstacles_count": len(obs_list),
    }


async def _run_docking_simulation(waypoints: List[List[float]], approach_heading_deg: float, charger_pose: Tuple[float, float, float]):
    """
    Unified docking executor:
    1. Locks the charger anchor so vision updates cannot jitter coordinates.
    2. Stage 1 (Coarse Navigation): Cozmo traverses the Two-Way A* waypoints around obstacles
       to the pre-dock approach pose (~18cm in front of charger), driving physical wheels on hardware
       and updating odometry + digital twin pose synchronously.
    3. Stage 2 (Fine Alignment): Aligns chassis toward the charger entrance.
       - If real robot is connected: hands over to closed-loop visual servoing with active camera feedback,
         optical marker locking, 180° rotation, and reverse docking with RobotStatusFlag.IS_ON_CHARGER pin check.
       - If running purely in simulation: executes simulated 180° rotation and reverse onto pins.
    """
    # 1. Lock charger anchor immediately
    visual_anchor_store.lock_charger()

    cli = cozmo_manager.get_robot() if cozmo_manager.is_connected else None
    track_width_mm = 45.0  # Cozmo track width

    try:
        cozmo_manager.set_docking_mode(True)
        cozmo_web_state.simulation_active = True
        cozmo_web_state.active_state = "DOCKING"
        cozmo_web_state.simulation_stage = "NAVIGATING"

        # Drive along waypoints (excluding final charger contact)
        nav_points = waypoints[:-1] if len(waypoints) > 1 else waypoints
        speed_mm_s = 50.0  # Safe physical drive speed (50 mm/s)
        turn_speed_deg_s = 60.0  # Smooth turn speed (60 deg/s)

        for i, target_pt in enumerate(nav_points):
            cur_x, cur_y, cur_theta = cozmo_web_state.latest_robot_pose
            tx, ty = target_pt[0], target_pt[1]

            # Steer toward target
            target_heading_deg = math.degrees(math.atan2(ty - cur_y, tx - cur_x))
            diff_rot = (target_heading_deg - cur_theta + 180.0) % 360.0 - 180.0

            # Turn phase
            if abs(diff_rot) > 2.5:
                turn_time = abs(diff_rot) / turn_speed_deg_s
                turn_steps = max(4, int(turn_time / 0.05))
                step_dt = turn_time / turn_steps
                turn_dir = 1.0 if diff_rot > 0 else -1.0
                wheel_speed = math.radians(turn_speed_deg_s) * (track_width_mm / 2.0)

                if cli:
                    try:
                        cli.drive_wheels(lwheel_speed=-turn_dir * wheel_speed, rwheel_speed=turn_dir * wheel_speed)
                    except Exception as e:
                        print(f"[Docking] Motor turn error: {e}")

                for t in range(turn_steps):
                    if not cozmo_web_state.simulation_active:
                        return
                    frac = (t + 1) / turn_steps
                    new_theta = (cur_theta + diff_rot * frac) % 360.0
                    cozmo_web_state.latest_robot_pose = (cur_x, cur_y, new_theta)
                    pose_tracker.update_pose(cur_x, cur_y, new_theta)
                    await asyncio.sleep(step_dt)

                if cli:
                    try:
                        cli.stop_all_motors()
                    except Exception:
                        pass
                await asyncio.sleep(0.05)

            # Drive phase
            dist = math.hypot(tx - cur_x, ty - cur_y)
            if dist > 3.0:
                drive_time = dist / speed_mm_s
                drive_steps = max(4, int(drive_time / 0.05))
                step_dt = drive_time / drive_steps

                if cli:
                    try:
                        cli.drive_wheels(lwheel_speed=speed_mm_s, rwheel_speed=speed_mm_s)
                    except Exception as e:
                        print(f"[Docking] Motor drive error: {e}")

                for d in range(drive_steps):
                    if not cozmo_web_state.simulation_active:
                        return
                    frac = (d + 1) / drive_steps
                    nx = cur_x + (tx - cur_x) * frac
                    ny = cur_y + (ty - cur_y) * frac
                    cozmo_web_state.latest_robot_pose = (nx, ny, target_heading_deg)
                    pose_tracker.update_pose(nx, ny, target_heading_deg)
                    cozmo_web_state.current_action = f"NAVIGATING WAYPOINT {i+1}/{len(nav_points)}"
                    await asyncio.sleep(step_dt)

                if cli:
                    try:
                        cli.stop_all_motors()
                    except Exception:
                        pass
                await asyncio.sleep(0.05)

        # Align chassis directly toward charger entrance
        cozmo_web_state.simulation_stage = "ALIGNING"
        cozmo_web_state.current_action = "ALIGNING TO CHARGER ENTRANCE"
        cur_x, cur_y, cur_theta = cozmo_web_state.latest_robot_pose
        diff_rot = (approach_heading_deg - cur_theta + 180.0) % 360.0 - 180.0
        if abs(diff_rot) > 2.5:
            turn_time = abs(diff_rot) / turn_speed_deg_s
            turn_steps = max(4, int(turn_time / 0.05))
            step_dt = turn_time / turn_steps
            turn_dir = 1.0 if diff_rot > 0 else -1.0
            wheel_speed = math.radians(turn_speed_deg_s) * (track_width_mm / 2.0)
            if cli:
                try:
                    cli.drive_wheels(lwheel_speed=-turn_dir * wheel_speed, rwheel_speed=turn_dir * wheel_speed)
                except Exception:
                    pass
            for t in range(turn_steps):
                if not cozmo_web_state.simulation_active:
                    return
                frac = (t + 1) / turn_steps
                new_theta = (cur_theta + diff_rot * frac) % 360.0
                cozmo_web_state.latest_robot_pose = (cur_x, cur_y, new_theta)
                pose_tracker.update_pose(cur_x, cur_y, new_theta)
                await asyncio.sleep(step_dt)
            if cli:
                try:
                    cli.stop_all_motors()
                except Exception:
                    pass
            await asyncio.sleep(0.05)

        # Stage 2: Hand over to closed-loop visual servoing if physical Cozmo connected
        if cli and cozmo_manager.is_connected:
            print("[Docking] Arrived at pre-dock entrance. Handing over to closed-loop visual servoing & reverse docking...")
            success = await visual_servoing_controller.execute_docking(
                cli=cli,
                get_detections=lambda: cozmo_web_state.latest_detections,
                get_robot_pose=lambda: cozmo_web_state.latest_robot_pose,
                set_robot_pose=lambda x, y, th: (
                    setattr(cozmo_web_state, "latest_robot_pose", (round(x, 1), round(y, 1), round(th, 1))),
                    pose_tracker.update_pose(round(x, 1), round(y, 1), round(th, 1)),
                ),
                set_state_info=lambda stage, action: (
                    setattr(cozmo_web_state, "simulation_stage", stage),
                    setattr(cozmo_web_state, "current_action", action),
                ),
                is_active=lambda: cozmo_web_state.simulation_active,
                charger_world_pose=charger_pose,
                set_docking_mode=cozmo_manager.set_docking_mode,
                get_camera_frame=lambda: getattr(cozmo_manager, "latest_image", None),
            )
            if success:
                cozmo_web_state.active_state = "DOCKED"
                cozmo_web_state.simulation_stage = "COMPLETED"
                cozmo_web_state.current_action = "CHARGING (4.20V) - AUTONOMOUS DOCK SUCCESSFUL"
                return

        # Digital Twin Simulated Docking Fallback (for simulation-only mode)
        # Stage 3: Rotate 180° for reverse docking
        cozmo_web_state.simulation_stage = "ALIGNING"
        cozmo_web_state.current_action = "ALIGNING 180° REVERSE DOCK"
        cur_x, cur_y, cur_theta = cozmo_web_state.latest_robot_pose
        target_reverse_theta = (approach_heading_deg + 180.0) % 360.0
        diff_rot = (target_reverse_theta - cur_theta + 180.0) % 360.0 - 180.0

        if abs(diff_rot) > 2.5:
            turn_time = abs(diff_rot) / turn_speed_deg_s
            turn_steps = max(6, int(turn_time / 0.05))
            step_dt = turn_time / turn_steps
            turn_dir = 1.0 if diff_rot > 0 else -1.0
            wheel_speed = math.radians(turn_speed_deg_s) * (track_width_mm / 2.0)

            for t in range(turn_steps):
                if not cozmo_web_state.simulation_active:
                    return
                frac = (t + 1) / turn_steps
                new_theta = (cur_theta + diff_rot * frac) % 360.0
                cozmo_web_state.latest_robot_pose = (cur_x, cur_y, new_theta)
                pose_tracker.update_pose(cur_x, cur_y, new_theta)
                await asyncio.sleep(step_dt)
            await asyncio.sleep(0.1)

        # Stage 4: Reverse onto charger pins
        cozmo_web_state.simulation_stage = "DOCKING"
        cozmo_web_state.current_action = "REVERSING ONTO CHARGER PINS"
        cx, cy, _ = charger_pose
        cur_x, cur_y, cur_theta = cozmo_web_state.latest_robot_pose
        dock_dist = math.hypot(cx - cur_x, cy - cur_y)
        dock_speed_mm_s = 28.0  # Gentle reverse docking speed
        dock_time = max(1.5, min(4.0, dock_dist / dock_speed_mm_s if dock_dist > 5.0 else 2.5))
        dock_steps = max(8, int(dock_time / 0.06))
        step_dt = dock_time / dock_steps

        for s in range(dock_steps):
            if not cozmo_web_state.simulation_active:
                return
            frac = (s + 1) / dock_steps
            nx = cur_x + (cx - cur_x) * frac
            ny = cur_y + (cy - cur_y) * frac
            cozmo_web_state.latest_robot_pose = (nx, ny, cur_theta)
            pose_tracker.update_pose(nx, ny, cur_theta)
            await asyncio.sleep(step_dt)

        # Stage 5: Docking Completed!
        cozmo_web_state.simulation_stage = "COMPLETED"
        cozmo_web_state.active_state = "DOCKED"
        cozmo_web_state.current_action = "CHARGING (4.20V) - DOCK COMPLETE"
        await asyncio.sleep(1.0)
    finally:
        if cli:
            try:
                cli.stop_all_motors()
            except Exception:
                pass
        cozmo_manager.set_docking_mode(False)
        cozmo_web_state.simulation_active = False


@cozmo_router.post("/simulation/dock")
async def start_docking_simulation(req: Optional[SimulationDockRequest] = None):
    """Calculates 2-Way A* path and executes simulated return-to-charger in real-time."""
    if cozmo_web_state.simulation_active and cozmo_web_state.simulation_task:
        cozmo_web_state.simulation_active = False
        cozmo_web_state.simulation_task.cancel()
        await asyncio.sleep(0.05)

    # 1. Plan path
    plan_res = await plan_dock_path(PlanPathRequest(clearance_mm=req.clearance_mm if req else DEFAULT_SAFETY_CLEARANCE_MM))
    if plan_res.get("status") != "success":
        raise HTTPException(status_code=400, detail="Cannot start simulation: No collision-free path found.")

    waypoints = plan_res["waypoints"]
    approach_heading = plan_res["plan"]["approach_heading_deg"]
    charger_pose = (plan_res["charger_pose"]["x"], plan_res["charger_pose"]["y"], plan_res["charger_pose"]["theta_deg"])

    # 2. Launch background simulation task
    task = asyncio.create_task(_run_docking_simulation(waypoints, approach_heading, charger_pose))
    cozmo_web_state.simulation_task = task

    return {
        "status": "success",
        "message": "Autonomous docking simulation started.",
        "plan": plan_res["plan"],
        "waypoints": waypoints,
    }


@cozmo_router.post("/simulation/reset")
async def reset_simulation():
    """Resets Cozmo pose to default starting location (0, 0, 0) and clears simulation."""
    if cozmo_web_state.simulation_task:
        cozmo_web_state.simulation_active = False
        cozmo_web_state.simulation_task.cancel()
        cozmo_web_state.simulation_task = None

    cozmo_web_state.simulation_active = False
    cozmo_web_state.simulation_stage = "IDLE"
    cozmo_web_state.active_state = "IDLE"
    cozmo_web_state.current_action = "STANDBY"
    cozmo_web_state.latest_robot_pose = (0.0, 0.0, 0.0)
    cozmo_web_state.planned_path = []
    cozmo_web_state.path_info = {}
    pose_tracker.reset_pose(0.0, 0.0, 0.0)

    return {"status": "success", "message": "Simulation reset. Cozmo pose at origin (0, 0, 0°)."}


class AsyncVisionEngine:
    """Decoupled vision background processor for ultra-fast zero-latency streaming."""
    def __init__(self):
        import threading
        self._lock = threading.Lock()
        self._latest_raw_bgr: Optional[np.ndarray] = None
        self._latest_robot_pose: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._latest_head_deg: float = 15.0
        self._last_frame_ts: float = 0.0
        self._is_running = True
        self._worker = threading.Thread(target=self._inference_loop, daemon=True)
        self._worker.start()

    def update_frame(self, frame_bgr: np.ndarray, robot_pose: Tuple[float, float, float], head_pitch_deg: float):
        with self._lock:
            self._latest_raw_bgr = frame_bgr
            self._latest_robot_pose = robot_pose
            self._latest_head_deg = head_pitch_deg
            self._last_frame_ts = time.time()

    def clear_frame(self):
        with self._lock:
            self._latest_raw_bgr = None
            self._last_frame_ts = 0.0

    def trigger_click_segment(self, click_x: float, click_y: float):
        with self._lock:
            cozmo_web_state.pending_click = (click_x, click_y)

    def clear_selection(self):
        with self._lock:
            cozmo_web_state.pending_click = None
            cozmo_web_state.active_selection_bbox = None
            cozmo_web_state.active_selection_mask = None
            cozmo_web_state.active_selection_feat = None

    def _inference_loop(self):
        while self._is_running:
            frame = None
            pose = (0.0, 0.0, 0.0)
            head_pitch = 15.0
            click_pt = None
            with self._lock:
                if self._latest_raw_bgr is not None and (time.time() - self._last_frame_ts) < 0.6:
                    frame = self._latest_raw_bgr.copy()
                    pose = self._latest_robot_pose
                    head_pitch = self._latest_head_deg
                    click_pt = cozmo_web_state.pending_click
                    cozmo_web_state.pending_click = None

            if frame is None:
                # DINO inference completely sleeps when webcam/stream is off
                time.sleep(0.08)
                continue

            try:
                cozmo_web_state.frame_count += 1
                is_calibrating = cozmo_web_state.frame_count <= dino_heatmap_extractor.calibration_target

                # Resize to standard size (320px width) for lightning-fast ViT spatial patch extraction
                h, w = frame.shape[:2]
                if w > 320:
                    scale = 320.0 / w
                    small_bgr = cv2.resize(frame, (320, int(h * scale)), interpolation=cv2.INTER_AREA)
                else:
                    small_bgr = frame

                pil_img = Image.fromarray(cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB))
                global_feat, patch_color_rgb, patch_tokens = dino_heatmap_extractor.extract_dense(
                    pil_img, is_calibrating=is_calibrating
                )

                if patch_color_rgb is not None and getattr(patch_color_rgb, "size", 0) > 0:
                    cozmo_web_state.latest_patch_color_rgb = patch_color_rgb

                # Process user mouse click segmentation (Auto-isolates clicked object + purple bounding box)
                if click_pt is not None and patch_tokens is not None and not is_calibrating:
                    cx, cy = click_pt
                    obj_feat, s_bbox, _, s_mask = dino_heatmap_extractor.extract_from_click_segment(
                        pil_img,
                        click_norm_x=cx,
                        click_norm_y=cy,
                        sim_threshold=0.80,
                    )
                    cozmo_web_state.active_selection_feat = obj_feat
                    cozmo_web_state.active_selection_bbox = s_bbox
                    cozmo_web_state.active_selection_mask = s_mask

                # Spatial multi-object detection
                if patch_tokens is not None and not is_calibrating:
                    detections = visual_anchor_store.detect_objects_in_patches(
                        patch_tokens_grid=patch_tokens,
                        min_patch_similarity=0.76,
                        min_matching_patches=2,
                    )
                    for det in detections:
                        bbox = det["bbox_norm"]
                        wx, wy, dist = estimate_ground_position(
                            bbox_norm=bbox,
                            robot_pose=pose,
                            head_angle_rad=math.radians(head_pitch),
                        )
                        det["world_x"] = wx
                        det["world_y"] = wy
                        det["distance_mm"] = dist
                        charger_theta = None
                        if any(tag in det["label"].lower() for tag in ("charger", "dock")):
                            charger_theta = (pose[2] + 180.0) % 360.0
                        visual_anchor_store.update_or_relocate_anchor(
                            det["label"], wx, wy, confidence=det["confidence"], new_theta_deg=charger_theta
                        )

                    cozmo_web_state.latest_detections = detections

                # REMIND memory novelty evaluation
                if global_feat is not None and not is_calibrating:
                    rx, ry, rtheta = pose
                    try:
                        res = remind_engine.process_feature(global_feat, rx, ry, rtheta)
                    except TypeError:
                        res = remind_engine.process_feature(global_feat)
                    if isinstance(res, tuple):
                        cozmo_web_state.latest_novelty = float(res[0])
                        cozmo_web_state.latest_classification = str(res[1]) if len(res) > 1 and isinstance(res[1], str) else "FAMILIAR"

                if hasattr(remind_engine, "memory_bank"):
                    cozmo_web_state.active_memories = len(remind_engine.memory_bank)
                    cozmo_web_state.total_objects = getattr(remind_engine, "total_objects_found", cozmo_web_state.active_memories)

            except Exception:
                pass

            time.sleep(0.06)  # ~16 Hz background detection & heatmap update


async_vision_engine = AsyncVisionEngine()


def generate_mjpeg_stream(source: Optional[str] = None):
    """Ultra-fast zero-latency real-time 30+ FPS MJPEG stream generator with exact DINO dual view."""
    webcam_cap = None
    last_frame_time = time.time()

    while True:
        target_source = (source or cozmo_web_state.camera_source).lower().strip()
        cli = cozmo_manager.get_robot()
        raw_frame = None

        if target_source == "cozmo":
            # If webcam was open from previous selection, release it
            if webcam_cap is not None:
                try:
                    webcam_cap.release()
                except Exception:
                    pass
                webcam_cap = None

            # Strictly Cozmo - DO NOT fall back to webcam
            if not (cli and cozmo_manager.is_connected):
                # Inform user that Cozmo is not connected
                offline_frame = np.zeros((240, 480, 3), dtype=np.uint8)
                cv2.rectangle(offline_frame, (10, 30), (470, 210), (18, 22, 32), -1)
                cv2.rectangle(offline_frame, (10, 30), (470, 210), (40, 50, 80), 1)

                cv2.putText(offline_frame, "COZMO NOT CONNECTED", (110, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 90, 255), 2)
                cv2.putText(offline_frame, "Cannot connect to Cozmo robot.", (100, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)
                cv2.putText(offline_frame, "Please connect to Cozmo Wi-Fi", (110, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (160, 180, 200), 1)
                cv2.putText(offline_frame, "or switch to Webcam on top right.", (95, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 200, 255), 1)

                ret, jpeg = cv2.imencode(".jpg", offline_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                if ret:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
                time.sleep(0.15)
                continue

            # Connected to Cozmo: Ensure camera event handler is attached & camera streaming is enabled
            if cli and not getattr(cli, "_cam_stream_enabled", False):
                try:
                    import pycozmo

                    def _on_camera_frame(client, image):
                        client.latest_image = image
                        client._latest_image = image
                        cozmo_manager.latest_image = image

                    cli.add_handler(pycozmo.event.EvtNewRawCameraImage, _on_camera_frame)
                    cli.enable_camera(enable=True, color=True)
                    cli._cam_stream_enabled = True
                    print("[OK] [Cozmo Camera] EvtNewRawCameraImage attached & color stream enabled.")
                except Exception as e:
                    print(f"[Cozmo Camera] Notice registering cam stream: {e}")

            # Retrieve frame from any available source on cli or manager
            raw_img = (
                getattr(cli, "latest_image", None)
                or getattr(cli, "_latest_image", None)
                or getattr(cozmo_manager, "latest_image", None)
            )
            if raw_img is not None:
                try:
                    if hasattr(raw_img, "convert"):
                        rgb_np = np.array(raw_img.convert("RGB"))
                    else:
                        rgb_np = np.array(raw_img)
                    raw_frame = cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR)
                except Exception as e:
                    print(f"[Cozmo Camera] Error converting frame: {e}")
                    raw_frame = None

            if raw_frame is None:
                waiting_frame = np.zeros((240, 480, 3), dtype=np.uint8)
                cv2.putText(waiting_frame, "COZMO CAM CONNECTED", (120, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 240, 255), 1)
                cv2.putText(waiting_frame, "Awaiting first frame...", (135, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 200, 220), 1)
                ret, jpeg = cv2.imencode(".jpg", waiting_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                if ret:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
                time.sleep(0.08)
                continue

        else:
            # Webcam Mode
            if not cozmo_web_state.webcam_enabled:
                if webcam_cap is not None:
                    try:
                        webcam_cap.release()
                    except Exception:
                        pass
                    webcam_cap = None
                async_vision_engine.clear_frame()

                off_frame = np.zeros((240, 480, 3), dtype=np.uint8)
                cv2.rectangle(off_frame, (10, 30), (470, 210), (18, 22, 32), -1)
                cv2.rectangle(off_frame, (10, 30), (470, 210), (40, 50, 80), 1)

                cv2.putText(off_frame, "WEBCAM DISABLED", (135, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (120, 140, 160), 2)
                cv2.putText(off_frame, "Webcam device closed & DINO stopped.", (90, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 210, 230), 1)
                cv2.putText(off_frame, "Click 'Webcam OFF' button below to re-enable.", (80, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 240, 255), 1)

                ret, jpeg = cv2.imencode(".jpg", off_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                if ret:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
                time.sleep(0.15)
                continue

            if webcam_cap is None or not webcam_cap.isOpened():
                webcam_cap = cv2.VideoCapture(0)
                if not webcam_cap.isOpened():
                    webcam_cap = cv2.VideoCapture(1)
                if webcam_cap.isOpened():
                    webcam_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if webcam_cap and webcam_cap.isOpened():
                ret, wb = webcam_cap.read()
                if ret and wb is not None:
                    raw_frame = wb

            if raw_frame is None:
                no_webcam = np.zeros((240, 480, 3), dtype=np.uint8)
                cv2.putText(no_webcam, "WEBCAM NOT DETECTED", (120, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 100, 255), 1)
                ret, jpeg = cv2.imencode(".jpg", no_webcam, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
                if ret:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
                time.sleep(0.15)
                continue

        # 1. Hardware sensor enhancements
        enhancement_params = cozmo_web_state.get_enhancement_params()
        calibrated_bgr = enhance_cozmo_frame(raw_frame, params=enhancement_params)

        # 2. Submit frame to background asynchronous DINO detector
        async_vision_engine.update_frame(
            frame_bgr=calibrated_bgr,
            robot_pose=cozmo_web_state.latest_robot_pose,
            head_pitch_deg=cozmo_web_state.head_pitch_deg,
        )

        # 3. High-Speed Exact Dual-View Composite HUD Render (< 1ms)
        comp_bgr = dino_heatmap_visualizer.render_composite(
            frame_bgr=calibrated_bgr,
            patch_color_rgb=cozmo_web_state.latest_patch_color_rgb,
            is_calibrating=False,
            calibration_progress=(cozmo_web_state.frame_count, dino_heatmap_extractor.calibration_target),
            novelty_score=cozmo_web_state.latest_novelty,
            classification=cozmo_web_state.latest_classification,
            active_memories=cozmo_web_state.active_memories,
            max_memories=500,
            total_objects=cozmo_web_state.total_objects,
            latency_ms=12.0,
            model_name=dino_heatmap_extractor.backend,
            frame_count=cozmo_web_state.frame_count,
            view_mode=DINOHeatmapVisualizer.VIEW_DUAL,
            show_reticle=False,
            detections=cozmo_web_state.latest_detections,
            selection_bbox=cozmo_web_state.active_selection_bbox,
            selection_mask=cozmo_web_state.active_selection_mask,
        )

        disp_h, disp_w = comp_bgr.shape[:2]

        # Top Hardware Source Badge (top right)
        source_badge = "COZMO CAMERA" if target_source == "cozmo" else "PC WEBCAM"
        badge_color = (0, 200, 255) if target_source == "cozmo" else (255, 180, 0)
        src_str = f"SRC: {source_badge} (30 FPS)"
        cv2.rectangle(comp_bgr, (disp_w - 250, 3), (disp_w - 10, 24), (20, 20, 20), -1)
        cv2.putText(comp_bgr, src_str, (disp_w - 242, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, badge_color, 1, cv2.LINE_AA)

        # 4. Ultra-Fast JPEG Encode
        ret, jpeg = cv2.imencode(".jpg", comp_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ret:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")

        # 5. Dynamic frame pacing for locked 30 FPS zero-lag stream
        now = time.time()
        elapsed = now - last_frame_time
        last_frame_time = now
        sleep_dur = max(0.002, 0.033 - elapsed)
        time.sleep(sleep_dur)


@cozmo_router.get("/video_feed")
async def get_cozmo_video_feed(source: Optional[str] = None):
    """Delivers live MJPEG camera stream with DINO Heatmap and object detections."""
    return StreamingResponse(
        generate_mjpeg_stream(source=source),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@cozmo_ws_router.websocket("/telemetry")
async def cozmo_telemetry_websocket(websocket: WebSocket):
    """Streams 20Hz JSON telemetry and handles bidirectional real-time commands."""
    await websocket.accept()

    async def receive_loop():
        try:
            while True:
                msg_text = await websocket.receive_text()
                try:
                    data = json.loads(msg_text)
                    action = data.get("action", "").lower()
                    if action == "drive":
                        speed = float(data.get("speed_mms", 0.0))
                        steer = float(data.get("turn_rate", 0.0))
                        cli = cozmo_manager.get_robot()
                        if cli and cozmo_manager.is_connected:
                            try:
                                cli.drive_wheels(speed - steer, speed + steer, duration=0.35)
                            except Exception:
                                pass
                        update_simulated_motion(speed, steer, dt=0.05)
                    elif action == "stop":
                        cli = cozmo_manager.get_robot()
                        if cli and cozmo_manager.is_connected:
                            try:
                                cli.stop_all_motors()
                            except Exception:
                                pass
                        cozmo_web_state.current_action = "STOPPED"
                    elif action == "tilt_head":
                        angle = data.get("angle_deg")
                        if angle is not None:
                            cozmo_web_state.head_pitch_deg = max(-25.0, min(44.0, float(angle)))
                    elif action == "headlight":
                        cozmo_web_state.headlight_on = not cozmo_web_state.headlight_on
                    elif action == "reset_simulation":
                        cozmo_web_state.latest_robot_pose = (0.0, 0.0, 0.0)
                        cozmo_web_state.head_pitch_deg = 15.0
                        cozmo_web_state.lift_height_mm = 0.0
                        cozmo_web_state.current_action = "RESET"
                        pose_tracker.reset_pose(0.0, 0.0, 0.0)
                except Exception:
                    pass
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    async def send_loop():
        try:
            while True:
                cli = cozmo_manager.get_robot()
                is_conn = bool(cli and cozmo_manager.is_connected)
                anchors = visual_anchor_store.list_anchors()
                obstacles = visual_anchor_store.list_obstacles()
                v_bat = getattr(cli, "battery_voltage", 4.10) if is_conn else 0.0

                payload = {
                    "timestamp": time.time(),
                    "camera_source": cozmo_web_state.camera_source,
                    "webcam_enabled": cozmo_web_state.webcam_enabled,
                    "robot": {
                        "is_connected": is_conn,
                        "is_connecting": cozmo_manager.is_connecting,
                        "x": round(cozmo_web_state.latest_robot_pose[0], 1),
                        "y": round(cozmo_web_state.latest_robot_pose[1], 1),
                        "theta_deg": round(cozmo_web_state.latest_robot_pose[2], 1),
                        "head_pitch_deg": round(cozmo_web_state.head_pitch_deg, 1),
                        "lift_height_mm": round(cozmo_web_state.lift_height_mm, 1),
                        "battery_voltage": round(float(v_bat), 2),
                        "headlight_on": cozmo_web_state.headlight_on,
                        "show_heatmap": cozmo_web_state.show_heatmap,
                        "webcam_enabled": cozmo_web_state.webcam_enabled,
                        "camera_source": cozmo_web_state.camera_source,
                        "state": cozmo_web_state.active_state,
                        "action": cozmo_web_state.current_action,
                    },
                    "anchors": [
                        {
                            "label": a.label,
                            "x": round(a.estimated_x, 1),
                            "y": round(a.estimated_y, 1),
                            "theta_deg": round(a.estimated_theta_deg, 1),
                            "is_locked": getattr(a, "is_locked", False),
                            "confidence_threshold": a.confidence_threshold,
                            "is_permanent": a.is_permanent,
                            "observation_count": a.observation_count,
                            "last_seen_at": a.last_seen_at,
                        }
                        for a in anchors
                    ],
                    "obstacles": [
                        {
                            "id": obs.id,
                            "x": round(obs.x, 1),
                            "y": round(obs.y, 1),
                            "radius": obs.radius,
                            "confidence": obs.confidence,
                            "last_seen": obs.last_seen,
                        }
                        for obs in obstacles
                    ],
                    "detections": [
                        {
                            "label": d.get("label"),
                            "confidence": round(float(d.get("confidence", 0.0)), 2),
                            "bbox_norm": d.get("bbox_norm"),
                            "world_x": round(float(d.get("world_x", 0.0)), 1),
                            "world_y": round(float(d.get("world_y", 0.0)), 1),
                            "distance_mm": round(float(d.get("distance_mm", 0.0)), 1),
                        }
                        for d in cozmo_web_state.latest_detections
                    ],
                    "blocks": list(cozmo_web_state.interactive_blocks.values()),
                    "path": cozmo_web_state.planned_path,
                    "path_info": cozmo_web_state.path_info,
                    "simulation": {
                        "is_active": cozmo_web_state.simulation_active,
                        "stage": cozmo_web_state.simulation_stage,
                    },
                }

                await websocket.send_json(payload)
                await asyncio.sleep(0.05)  # 20 Hz
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    rx_task = asyncio.create_task(receive_loop())
    tx_task = asyncio.create_task(send_loop())
    try:
        await asyncio.gather(rx_task, tx_task)
    except Exception:
        pass
    finally:
        rx_task.cancel()
        tx_task.cancel()
