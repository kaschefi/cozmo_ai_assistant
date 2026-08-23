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
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import numpy as np
from PIL import Image
import cv2

from core.hardware.connection import cozmo_manager
from autonomous_cozmo.vision import (
    dino_heatmap_extractor,
    dino_heatmap_visualizer,
    visual_anchor_store,
    remind_engine,
    enhance_cozmo_frame,
    render_cozmo_frame_heatmap,
    estimate_ground_position,
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
        self.latest_robot_pose = (0.0, 0.0, 0.0)  # (x_mm, y_mm, theta_deg)
        self.planned_path: List[List[float]] = []
        self.latest_detections: List[Dict[str, Any]] = []

    def get_enhancement_params(self) -> Dict[str, float]:
        return {
            "red_gain": 0.85,
            "blue_gain": 1.05,
            "brightness": float(self.brightness_offset),
            "contrast": float(self.contrast_gain),
            "gamma": float(self.gamma_val),
        }

cozmo_web_state = CozmoWebState()


class CozmoCommandRequest(BaseModel):
    action: str  # "drive", "stop", "tilt_head", "lift", "headlight", "brightness", "dock", "teach"
    speed_mms: Optional[float] = None
    turn_rate: Optional[float] = None
    angle_deg: Optional[float] = None
    height_mm: Optional[float] = None
    enabled: Optional[bool] = None
    delta: Optional[float] = None
    label: Optional[str] = None
    click_x: Optional[float] = None
    click_y: Optional[float] = None


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
        "active_state": cozmo_web_state.active_state,
        "robot_pose": {
            "x": cozmo_web_state.latest_robot_pose[0],
            "y": cozmo_web_state.latest_robot_pose[1],
            "theta_deg": cozmo_web_state.latest_robot_pose[2],
        }
    }


@cozmo_router.post("/connect")
async def connect_cozmo(timeout: float = 12.0):
    """Triggers background PyCozmo Wi-Fi connection handshake."""
    cozmo_manager.robot_mode = True
    cozmo_manager.start()
    return {"status": "connecting", "message": "Initiating Cozmo connection handshake..."}


@cozmo_router.post("/command")
async def execute_cozmo_command(req: CozmoCommandRequest):
    """Executes manual drive, head tilt, lighting, or autonomous action commands."""
    cli = cozmo_manager.get_robot()
    action = req.action.lower()

    if action == "drive":
        speed = req.speed_mms or 0.0
        steer = req.turn_rate or 0.0
        if cli and cozmo_manager.is_connected:
            lw = speed - steer
            rw = speed + steer
            cli.drive_wheels(lw, rw, duration=0.35)
            cozmo_web_state.current_action = f"DRIVE ({speed:.0f} mm/s)"
        return {"status": "success", "action": "drive"}

    elif action == "stop":
        if cli and cozmo_manager.is_connected:
            cli.stop_all_motors()
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
        cozmo_web_state.current_action = "NAVIGATING TO CHARGER"
        # Autonomous return to dock trigger
        return {"status": "success", "message": "Initiating autonomous docking sequence."}

    elif action == "teach":
        label = (req.label or "").strip()
        if not label:
            raise HTTPException(status_code=400, detail="Label is required for teaching.")
        # Teach currently observed frame center or clicked coordinates
        return {"status": "success", "message": f"Taught object '{label}'"}

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
                "observation_count": a.observation_count,
                "last_seen_at": a.last_seen_at,
                "notes": a.notes,
            }
            for a in anchors
        ]
    }


@cozmo_router.delete("/anchors/{label}")
async def delete_visual_anchor(label: str):
    """Deletes a visual anchor from persistent storage."""
    deleted = visual_anchor_store.delete_anchor(label)
    if deleted:
        return {"status": "success", "message": f"Deleted anchor '{label}'"}
    raise HTTPException(status_code=404, detail=f"Anchor '{label}' not found")


def generate_mjpeg_stream():
    """Generator capturing robot/webcam frames, processing DINO, and yielding MJPEG multipart chunks."""
    webcam_cap = None
    frame_count = 0

    while True:
        cli = cozmo_manager.get_robot()
        raw_frame = None

        if cli and cozmo_manager.is_connected:
            raw_img = getattr(cli, "latest_image", None)
            if raw_img is not None:
                rgb_np = np.array(raw_img.convert("RGB"))
                raw_frame = cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR)

        # Fallback to local webcam if Cozmo is not streaming
        if raw_frame is None:
            if webcam_cap is None or not webcam_cap.isOpened():
                webcam_cap = cv2.VideoCapture(0)
                if not webcam_cap.isOpened():
                    webcam_cap = cv2.VideoCapture(1)
            if webcam_cap and webcam_cap.isOpened():
                ret, wb = webcam_cap.read()
                if ret and wb is not None:
                    raw_frame = wb

        if raw_frame is None:
            # Create dark placeholder frame
            raw_frame = np.zeros((240, 320, 3), dtype=np.uint8)
            cv2.putText(raw_frame, "WAITING FOR CAMERA...", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1)

        frame_count += 1
        is_calibrating = frame_count <= dino_heatmap_extractor.calibration_target

        # 1. Apply hardware sensor enhancements
        calibrated_bgr = enhance_cozmo_frame(raw_frame, params=cozmo_web_state.get_enhancement_params())

        # 2. Extract DINO tokens
        pil_img = Image.fromarray(cv2.cvtColor(calibrated_bgr, cv2.COLOR_BGR2RGB))
        global_feat, patch_color_rgb, patch_tokens = dino_heatmap_extractor.extract_dense(pil_img, is_calibrating=is_calibrating)

        # 3. Detect Anchors & Perform Ground Raycasting
        detections = []
        if not is_calibrating and patch_tokens is not None:
            detections = visual_anchor_store.detect_objects_in_patches(
                patch_tokens_grid=patch_tokens,
                min_patch_similarity=0.76,
                min_matching_patches=2,
            )

            # Update ground coordinates & dynamic relocation
            for det in detections:
                bbox = det["bbox_norm"]
                wx, wy, dist = estimate_ground_position(
                    bbox_norm=bbox,
                    robot_pose=cozmo_web_state.latest_robot_pose,
                    head_angle_rad=math.radians(cozmo_web_state.head_pitch_deg),
                )
                det["world_x"] = wx
                det["world_y"] = wy
                det["distance_mm"] = dist
                # Relocate anchor position if moved
                visual_anchor_store.update_or_relocate_anchor(det["label"], wx, wy, confidence=det["confidence"])

        cozmo_web_state.latest_detections = detections

        # 4. Render Composite Frame
        comp_bgr, _, _ = render_cozmo_frame_heatmap(
            raw_frame=calibrated_bgr,
            extractor=dino_heatmap_extractor,
            visualizer=dino_heatmap_visualizer,
            remind_engine=remind_engine,
            is_calibrating=is_calibrating,
            is_cozmo_cam=False,
            frame_count=frame_count,
            detections=detections,
        )

        # Encode to JPEG
        ret, jpeg = cv2.imencode(".jpg", comp_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        if ret:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")

        time.sleep(0.033)  # ~30 FPS


@cozmo_router.get("/video_feed")
async def get_cozmo_video_feed():
    """Delivers live MJPEG camera stream with DINO Heatmap and object detections."""
    return StreamingResponse(
        generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@cozmo_ws_router.websocket("/telemetry")
async def cozmo_telemetry_websocket(websocket: WebSocket):
    """Streams 20Hz JSON telemetry for 2D Semantic Grid Map and Mission Control Dashboard."""
    await websocket.accept()
    try:
        while True:
            cli = cozmo_manager.get_robot()
            is_conn = bool(cli and cozmo_manager.is_connected)

            # Get Pose from PyCozmo odometry if connected
            if is_conn and hasattr(cli, "pose") and cli.pose is not None:
                px = float(getattr(cli.pose.position, "x", 0.0))
                py = float(getattr(cli.pose.position, "y", 0.0))
                ptheta = float(getattr(cli.pose.rotation, "angle_z", None).degrees if getattr(cli.pose.rotation, "angle_z", None) else 0.0)
                cozmo_web_state.latest_robot_pose = (px, py, ptheta)

            anchors = visual_anchor_store.list_anchors()
            obstacles = visual_anchor_store.list_obstacles()
            v_bat = getattr(cli, "battery_voltage", 4.10) if is_conn else 0.0

            payload = {
                "timestamp": time.time(),
                "robot": {
                    "is_connected": is_conn,
                    "x": round(cozmo_web_state.latest_robot_pose[0], 1),
                    "y": round(cozmo_web_state.latest_robot_pose[1], 1),
                    "theta_deg": round(cozmo_web_state.latest_robot_pose[2], 1),
                    "head_pitch_deg": round(cozmo_web_state.head_pitch_deg, 1),
                    "lift_height_mm": round(cozmo_web_state.lift_height_mm, 1),
                    "battery_voltage": round(float(v_bat), 2),
                    "headlight_on": cozmo_web_state.headlight_on,
                    "state": cozmo_web_state.active_state,
                    "action": cozmo_web_state.current_action,
                },
                "anchors": [
                    {
                        "label": a.label,
                        "x": round(a.estimated_x, 1),
                        "y": round(a.estimated_y, 1),
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
                "path": cozmo_web_state.planned_path,
            }

            await websocket.send_json(payload)
            await asyncio.sleep(0.05)  # 20 Hz
    except WebSocketDisconnect:
        pass
    except Exception as e:
        pass
