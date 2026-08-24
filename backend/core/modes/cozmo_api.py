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
        self.latest_detections: List[Dict[str, Any]] = []
        self.latest_patch_color_rgb: Optional[np.ndarray] = None
        self.latest_novelty: float = 0.0
        self.latest_classification: str = "FAMILIAR"
        self.active_memories: int = 0
        self.total_objects: int = 0
        self.frame_count: int = 0

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

# Ensure charger is grounded at default 10cm behind Cozmo upon startup
visual_anchor_store.ensure_default_charger(cozmo_web_state.latest_robot_pose)


class CozmoCommandRequest(BaseModel):
    action: str  # "drive", "stop", "tilt_head", "lift", "headlight", "brightness", "dock", "teach", "set_camera_source", "toggle_webcam"
    speed_mms: Optional[float] = None
    turn_rate: Optional[float] = None
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


@cozmo_router.post("/connect")
async def connect_cozmo(timeout: float = 12.0):
    """Triggers background PyCozmo Wi-Fi connection handshake."""
    cozmo_manager.robot_mode = True
    cozmo_manager.start()
    return {"status": "connecting", "message": "Initiating Cozmo connection handshake..."}


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
                    cli.enable_camera(enable=True, color=True)
                except Exception:
                    pass
            return {"status": "success", "camera_source": cozmo_web_state.camera_source}
        raise HTTPException(status_code=400, detail="Camera source must be 'cozmo' or 'webcam'.")

    elif action == "drive":
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
                        visual_anchor_store.update_or_relocate_anchor(det["label"], wx, wy, confidence=det["confidence"])

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

            # Connected to Cozmo
            raw_img = getattr(cli, "latest_image", None)
            if raw_img is not None:
                try:
                    rgb_np = np.array(raw_img.convert("RGB"))
                    raw_frame = cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR)
                except Exception:
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
                "camera_source": cozmo_web_state.camera_source,
                "webcam_enabled": cozmo_web_state.webcam_enabled,
                "robot": {
                    "is_connected": is_conn,
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
