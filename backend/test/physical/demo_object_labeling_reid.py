"""
Moka AI Assistant - Autonomous Cozmo Vision Subsystem
Interactive Object Teaching & Persistent Spatial Re-Identification Demo (Milestone 5.1).

Upgraded Capabilities:
  1. Live Camera Hot-Swapping: Switch dynamically between Webcam and Cozmo Camera during runtime (Press TAB or 'V').
  2. Full Robot Teleoperation: Drive Cozmo (WASD / Arrows) and tilt head up/down (I / K) directly from the stream!
  3. Dynamic Camera Lighting & Brightness Controls:
     - Toggle physical Cozmo headlights (Press 'O' or 'P')
     - Adjust camera brightness gain (Press '[' / ']' or 'B')
     - Adjust gamma exposure curve (Press '-' / '+')
     - Reset lighting to calibrated defaults (Press '0')
  4. Interactive Mouse Click-to-Segment: Click ANY object (or charger) to auto-isolate its DINO patch cluster,
     completely ignoring hands, fingers, and background!
  5. Interactive Mouse Drag-to-Box: Click and drag custom ROI bounding boxes.
  6. Spatial Patch Multi-Object Bounding Boxes: Real-time localization of multiple objects simultaneously.

Usage:
  python backend/test/physical/demo_object_labeling_reid.py
  python backend/test/physical/demo_object_labeling_reid.py --source cozmo
  python backend/test/physical/demo_object_labeling_reid.py --source webcam

Controls:
  --- Video & Vision Controls ---
  - Left-Click on Object : Auto-segment and select the clicked object (ignoring hands & background)
  - Left-Drag on Stream  : Draw a custom bounding box around any area
  - Right-Click          : Clear active mouse selection
  - Press 't' in window  : Teach / Label the clicked/selected object (saves to visual_anchors.json)
  - Press TAB or 'v'     : Switch Camera Source (Webcam <-> Cozmo Camera)
  - Press 'm' in window  : Cycle View Mode (Dual-View -> Blended -> Heatmap-Only -> Clean)
  - Press 'l' in window  : List all saved anchors & coordinates in terminal
  - Press 'd' in window  : Delete a saved anchor
  - Press 'r' in window  : Recalibrate Retinal Matrix
  - Press 'c' in window  : Clear transient memory bank
  - Press 'q' or ESC     : Exit Demo

  --- Camera Lighting & Brightness ---
  - O / P                : Toggle Physical Cozmo Headlights (ON / OFF)
  - [ / ]                : Decrease / Increase Camera Brightness (-10 / +10)
  - - / + (or =)         : Decrease / Increase Gamma Exposure Curve (-0.10 / +0.10)
  - 0 (Zero)             : Reset Brightness & Exposure to Defaults

  --- Robot Teleoperation (when Cozmo is active) ---
  - W / Up Arrow         : Drive Forward
  - S / Down Arrow       : Drive Backward
  - A / Left Arrow       : Turn Left
  - D / Right Arrow      : Turn Right
  - SPACEBAR / X         : Stop Wheels Immediately
  - I / Page Up          : Tilt Head UP (+5°)
  - K / Page Down        : Tilt Head DOWN (-5°)
  - H                    : Reset Head to Horizontal (0°)
  - U                    : Lift Arm UP
  - J                    : Lower Arm DOWN
"""

import os
import sys
import time
import math
import argparse
from typing import Optional, List, Dict, Tuple, Union, Any
import numpy as np
from PIL import Image
import cv2

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from autonomous_cozmo.vision import (
    DINOPrecisionExtractor,
    DINOHeatmapVisualizer,
    enhance_cozmo_frame,
    render_cozmo_frame_heatmap,
    visual_anchor_store,
    REMINDMemoryEngine,
    remind_engine,
)

# Terminal formatting colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


class MouseInteractionState:
    """Tracks interactive mouse clicks, drags, and object segmentation in OpenCV."""
    def __init__(self):
        self.clicked_point = None      # (norm_x, norm_y)
        self.drag_start = None         # (norm_x, norm_y)
        self.drag_current = None       # (norm_x, norm_y)
        self.is_dragging = False
        self.selected_bbox = None      # (ymin, xmin, ymax, xmax)
        self.selected_mask = None      # (grid_h, grid_w) boolean
        self.selected_feature = None   # (384,)
        self.selection_type = "none"   # "click", "drag", "none"
        self.full_w = 640
        self.full_h = 480
        self.is_dual = True

    def on_mouse(self, event, x, y, flags, param):
        pane_w = self.full_w // 2 if self.is_dual else self.full_w
        norm_x = min(1.0, max(0.0, (x % pane_w) / float(pane_w)))
        norm_y = min(1.0, max(0.0, y / float(self.full_h)))

        if event == cv2.EVENT_LBUTTONDOWN:
            self.drag_start = (norm_x, norm_y)
            self.drag_current = (norm_x, norm_y)
            self.is_dragging = False
            self.clicked_point = (norm_x, norm_y)
            self.selection_type = "click"

        elif event == cv2.EVENT_MOUSEMOVE:
            if (flags & cv2.EVENT_FLAG_LBUTTON) and self.drag_start is not None:
                dx = abs(norm_x - self.drag_start[0])
                dy = abs(norm_y - self.drag_start[1])
                if dx > 0.02 or dy > 0.02:
                    self.is_dragging = True
                    self.drag_current = (norm_x, norm_y)
                    self.selection_type = "drag"

        elif event == cv2.EVENT_LBUTTONUP:
            if self.is_dragging and self.drag_start is not None:
                xmin = min(self.drag_start[0], norm_x)
                xmax = max(self.drag_start[0], norm_x)
                ymin = min(self.drag_start[1], norm_y)
                ymax = max(self.drag_start[1], norm_y)
                self.selected_bbox = (ymin, xmin, ymax, xmax)
                self.selected_mask = None
                self.selection_type = "drag"
                self.is_dragging = False
            else:
                self.clicked_point = (norm_x, norm_y)
                self.selection_type = "click"
                self.is_dragging = False

        elif event == cv2.EVENT_RBUTTONDOWN:
            self.clear()
            print(f"{YELLOW}[Mouse] Selection cleared.{RESET}")

    def clear(self):
        self.clicked_point = None
        self.drag_start = None
        self.drag_current = None
        self.is_dragging = False
        self.selected_bbox = None
        self.selected_mask = None
        self.selected_feature = None
        self.selection_type = "none"


class CozmoHardwareController:
    """Manages PyCozmo client connection, camera stream, lighting, brightness, and driving."""
    def __init__(self):
        self.cli = None
        self.is_connected = False
        self.is_connecting = False
        self.latest_cozmo_frame = None
        self.head_angle_deg = 15.0
        self.lift_height_mm = 32.0
        self.current_action = "IDLE"
        self.last_drive_command_time = 0.0

        # Lighting & Exposure Parameters
        self.headlight_on = False
        self.brightness_offset = -15  # -100 to +100
        self.contrast_gain = 1.10     # 0.5 to 2.5
        self.gamma_val = 0.85         # 0.2 to 2.5

    def connect(self, timeout: float = 12.0) -> bool:
        if self.is_connected and self.cli:
            return True
        if self.is_connecting:
            return False

        print(f"{BLUE}[PyCozmo] Initializing robot connection...{RESET}")
        self.is_connecting = True
        try:
            import pycozmo
            from core.hardware.connection import cozmo_manager
            cozmo_manager.robot_mode = True
            cozmo_manager.start()
            cli = cozmo_manager.wait_for_connection(timeout=timeout)

            if cli:
                self.cli = cli
                self.is_connected = True
                self.is_connecting = False

                # Register Camera Stream
                def _on_cam(c, image):
                    self.latest_cozmo_frame = image

                try:
                    self.cli.add_handler(pycozmo.event.EvtNewRawCameraImage, _on_cam)
                    self.cli.enable_camera(enable=True, color=True)
                except Exception as e:
                    print(f"{YELLOW}[PyCozmo] Camera listener notice: {e}{RESET}")

                # Set initial head tilt
                self.set_head_angle(self.head_angle_deg)
                print(f"{GREEN}[OK] PyCozmo connected! Camera stream active.{RESET}")
                return True
            else:
                self.is_connecting = False
                print(f"{YELLOW}[Warning] PyCozmo connection timed out.{RESET}")
                return False
        except Exception as e:
            self.is_connecting = False
            print(f"{RED}[PyCozmo Error] Connection failed: {e}{RESET}")
            return False

    def get_latest_frame(self) -> Optional[np.ndarray]:
        if not self.is_connected or not self.cli:
            return None
        raw = self.latest_cozmo_frame or getattr(self.cli, "latest_image", None)
        if raw is not None:
            rgb_np = np.array(raw.convert("RGB"))
            return cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR)
        return None

    def toggle_headlight(self) -> bool:
        if self.is_connected and self.cli:
            self.headlight_on = not self.headlight_on
            try:
                if hasattr(self.cli, "set_head_light"):
                    self.cli.set_head_light(self.headlight_on)
                self.current_action = f"HEADLIGHT {'ON' if self.headlight_on else 'OFF'}"
                print(f"{CYAN}[Hardware Light] Headlights -> {'ON' if self.headlight_on else 'OFF'}{RESET}")
            except Exception as e:
                print(f"{YELLOW}[Hardware Light] Notice: {e}{RESET}")
            return self.headlight_on
        return False

    def adjust_brightness(self, delta: int = 10):
        self.brightness_offset = max(-100, min(100, self.brightness_offset + delta))
        self.current_action = f"BRIGHTNESS {self.brightness_offset:+d}"
        print(f"{CYAN}[Camera Exposure] Brightness Offset -> {self.brightness_offset:+d}{RESET}")

    def adjust_gamma(self, delta: float = 0.10):
        self.gamma_val = max(0.20, min(2.50, round(self.gamma_val + delta, 2)))
        self.current_action = f"GAMMA {self.gamma_val:.2f}"
        print(f"{CYAN}[Camera Exposure] Gamma Curve -> {self.gamma_val:.2f}{RESET}")

    def reset_lighting(self):
        self.brightness_offset = -15
        self.contrast_gain = 1.10
        self.gamma_val = 0.85
        self.current_action = "EXPOSURE RESET"
        print(f"{CYAN}[Camera Exposure] Reset to defaults (Brightness: -15, Gamma: 0.85){RESET}")

    def get_enhancement_params(self) -> Dict[str, float]:
        return {
            "red_gain": 0.85,
            "blue_gain": 1.05,
            "brightness": float(self.brightness_offset),
            "contrast": float(self.contrast_gain),
            "gamma": float(self.gamma_val),
        }

    def drive_forward(self, speed_mms: float = 55.0):
        if self.is_connected and self.cli:
            self.cli.drive_wheels(speed_mms, speed_mms, duration=0.35)
            self.current_action = f"DRIVE FORWARD ({speed_mms:.0f} mm/s)"
            self.last_drive_command_time = time.time()

    def drive_backward(self, speed_mms: float = 55.0):
        if self.is_connected and self.cli:
            self.cli.drive_wheels(-speed_mms, -speed_mms, duration=0.35)
            self.current_action = f"DRIVE BACKWARD (-{speed_mms:.0f} mm/s)"
            self.last_drive_command_time = time.time()

    def turn_left(self, speed_mms: float = 40.0):
        if self.is_connected and self.cli:
            self.cli.drive_wheels(-speed_mms, speed_mms, duration=0.25)
            self.current_action = "TURN LEFT"
            self.last_drive_command_time = time.time()

    def turn_right(self, speed_mms: float = 40.0):
        if self.is_connected and self.cli:
            self.cli.drive_wheels(speed_mms, -speed_mms, duration=0.25)
            self.current_action = "TURN RIGHT"
            self.last_drive_command_time = time.time()

    def stop_wheels(self):
        if self.is_connected and self.cli:
            self.cli.stop_all_motors()
            self.current_action = "STOPPED"
            self.last_drive_command_time = time.time()

    def set_head_angle(self, angle_deg: float):
        if self.is_connected and self.cli:
            self.head_angle_deg = max(-25.0, min(44.0, angle_deg))
            rad = math.radians(self.head_angle_deg)
            try:
                self.cli.set_head_angle(rad)
                self.current_action = f"HEAD PITCH {self.head_angle_deg:+.1f}°"
            except Exception:
                pass

    def tilt_head_up(self, step_deg: float = 6.0):
        self.set_head_angle(self.head_angle_deg + step_deg)

    def tilt_head_down(self, step_deg: float = 6.0):
        self.set_head_angle(self.head_angle_deg - step_deg)

    def set_lift_height(self, height_mm: float):
        if self.is_connected and self.cli:
            self.lift_height_mm = max(32.0, min(92.0, height_mm))
            try:
                self.cli.set_lift_height(self.lift_height_mm)
                self.current_action = f"LIFT {self.lift_height_mm:.0f}mm"
            except Exception:
                pass

    def get_battery_voltage(self) -> float:
        if self.is_connected and self.cli:
            return getattr(self.cli, "battery_voltage", 4.10) or 4.10
        return 0.0


def print_anchor_table():
    """Prints all persistently stored anchors in a formatted table."""
    anchors = visual_anchor_store.list_anchors()
    print(f"\n{CYAN}{'='*75}{RESET}")
    print(f"{CYAN}{BOLD}  CURRENT PERSISTENT VISUAL ANCHORS ({len(anchors)} stored in visual_anchors.json){RESET}")
    print(f"{CYAN}{'='*75}{RESET}")
    if not anchors:
        print(f"  {YELLOW}(No visual anchors saved yet. Click on an object in stream and press 't'!){RESET}")
    else:
        for idx, a in enumerate(anchors, 1):
            perm_tag = f"{GREEN}[PERMANENT]{RESET}" if a.is_permanent else "[TRANSIENT]"
            print(
                f"  {idx}. {BOLD}{a.label:<16}{RESET} {perm_tag} | "
                f"Pos: ({a.estimated_x:.1f}, {a.estimated_y:.1f}) | "
                f"Hits: {a.observation_count:<3} | Threshold: {a.confidence_threshold:.2f}"
            )
    print(f"{CYAN}{'-'*75}{RESET}\n")


def run_interactive_teaching_demo(source: str = "webcam", model_backend: str = "dinov3"):
    print(f"\n{CYAN}{'='*75}{RESET}")
    print(f"{CYAN}{BOLD}   MOKA AI ASSISTANT -- PERSISTENT OBJECT TEACHING & RE-ID DEMO   {RESET}")
    print(f"{CYAN}{'='*75}{RESET}\n")

    print_anchor_table()

    # 1. Initialize Vision Engine, Mouse State & Robot Controller
    extractor = DINOPrecisionExtractor(backend=model_backend, calibration_frames=10)
    visualizer = DINOHeatmapVisualizer(default_view_mode=DINOHeatmapVisualizer.VIEW_DUAL)
    mouse_state = MouseInteractionState()
    cozmo_ctrl = CozmoHardwareController()

    active_source = source.lower()  # "webcam" or "cozmo"
    webcam_cap = None

    # Connect to initial source
    if active_source == "cozmo":
        if not cozmo_ctrl.connect(timeout=10.0):
            print(f"{YELLOW}[Notice] Falling back to webcam.{RESET}")
            active_source = "webcam"

    if active_source == "webcam":
        webcam_cap = cv2.VideoCapture(0)
        if not webcam_cap.isOpened():
            webcam_cap = cv2.VideoCapture(1)
        if webcam_cap.isOpened():
            webcam_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            webcam_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            print(f"{GREEN}[OK] Webcam initialized successfully!{RESET}")
        else:
            print(f"{YELLOW}[Notice] Webcam device not found.{RESET}")

    window_name = "Moka AI - Object Teaching & Persistent Re-ID"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window_name, mouse_state.on_mouse)

    print(f"\n{YELLOW}Stream & Control Reference:{RESET}")
    print(f"  - {BOLD}TAB / 'v'{RESET}            : Switch Camera Source (Webcam <-> Cozmo Camera)")
    print(f"  - {BOLD}Left-Click on Object{RESET} : Auto-segment object under cursor (isolates from hands!)")
    print(f"  - {BOLD}Left-Drag on Stream{RESET}  : Custom bounding box selection")
    print(f"  - {BOLD}Right-Click{RESET}          : Clear selection")
    print(f"  - Press {BOLD}'t'{RESET}             : Teach / Label the selected object (saves to visual_anchors.json)")
    print(f"  - Press {BOLD}'m'{RESET}             : Cycle View Mode (Dual-View -> Blended -> Heatmap -> Clean)")
    print(f"  - Press {BOLD}'l'{RESET}             : List all saved anchors & coordinates")
    print(f"  - Press {BOLD}'d'{RESET}             : Delete an anchor")
    print(f"  - Press {BOLD}'r'{RESET}             : Recalibrate Retinal Matrix")
    print(f"  - Press {BOLD}'c'{RESET}             : Clear transient memory bank")
    print(f"  - Press {BOLD}'q' / ESC{RESET}       : Exit Demo\n")
    print(f"{CYAN}Camera Lighting & Exposure Controls:{RESET}")
    print(f"  - {BOLD}O / P{RESET}                : Toggle Cozmo Headlights (ON / OFF)")
    print(f"  - {BOLD}[ / ]{RESET}                : Decrease / Increase Brightness Offset (-10 / +10)")
    print(f"  - {BOLD}- / +{RESET} (or =)         : Decrease / Increase Gamma Exposure (-0.10 / +0.10)")
    print(f"  - {BOLD}0 (Zero){RESET}             : Reset Lighting & Brightness to Defaults\n")
    print(f"{CYAN}Robot Teleoperation (Active when Cozmo is connected):{RESET}")
    print(f"  - {BOLD}W / S / A / D{RESET}        : Drive Forward / Backward / Turn Left / Turn Right")
    print(f"  - {BOLD}SPACEBAR / X{RESET}         : Stop Wheels")
    print(f"  - {BOLD}I / K{RESET}                : Tilt Head Up / Down (Pitch)")
    print(f"  - {BOLD}H{RESET}                    : Reset Head to 0° (Horizontal)")
    print(f"  - {BOLD}U / J{RESET}                : Raise / Lower Lift Arm\n")

    frame_count = 0

    try:
        while True:
            # 1. Grab frame from active camera
            frame_bgr = None
            is_cozmo_active = (active_source == "cozmo")

            if is_cozmo_active:
                frame_bgr = cozmo_ctrl.get_latest_frame()
                if frame_bgr is None:
                    time.sleep(0.015)
                    if webcam_cap and webcam_cap.isOpened():
                        ret, wb_frame = webcam_cap.read()
                        if ret and wb_frame is not None:
                            frame_bgr = wb_frame
            else:
                if webcam_cap and webcam_cap.isOpened():
                    ret, wb_frame = webcam_cap.read()
                    if ret and wb_frame is not None:
                        frame_bgr = wb_frame
                if frame_bgr is None and cozmo_ctrl.is_connected:
                    frame_bgr = cozmo_ctrl.get_latest_frame()

            if frame_bgr is None:
                time.sleep(0.02)
                continue

            frame_count += 1
            is_calibrating = frame_count <= extractor.calibration_target

            # 2. Hardware Enhancement & Dynamic Brightness Calibration
            if is_cozmo_active:
                calibrated_bgr = enhance_cozmo_frame(frame_bgr, params=cozmo_ctrl.get_enhancement_params())
            else:
                # If custom brightness/gamma set, apply enhancement to webcam as well
                if cozmo_ctrl.brightness_offset != -15 or cozmo_ctrl.gamma_val != 0.85:
                    calibrated_bgr = enhance_cozmo_frame(frame_bgr, params=cozmo_ctrl.get_enhancement_params())
                else:
                    calibrated_bgr = frame_bgr

            h, w, _ = calibrated_bgr.shape

            # Update mouse state dimensions
            mouse_state.full_w = w * 2 if visualizer.view_mode == DINOHeatmapVisualizer.VIEW_DUAL else w
            mouse_state.full_h = h
            mouse_state.is_dual = (visualizer.view_mode == DINOHeatmapVisualizer.VIEW_DUAL)

            # 3. Extract Dense Spatial Tokens & Heatmap
            pil_img = Image.fromarray(cv2.cvtColor(calibrated_bgr, cv2.COLOR_BGR2RGB))
            global_feat, patch_color_rgb, patch_tokens_spatial = extractor.extract_dense(pil_img, is_calibrating=is_calibrating)

            # 4. Process Interactive Mouse Selection / Flood-Fill Segmentation
            selection_bbox = None
            selection_mask = None

            if not is_calibrating and patch_tokens_spatial is not None:
                if mouse_state.selection_type == "click" and mouse_state.clicked_point is not None:
                    cx, cy = mouse_state.clicked_point
                    obj_feat, s_bbox, _, s_mask = extractor.extract_from_click_segment(
                        pil_img,
                        click_norm_x=cx,
                        click_norm_y=cy,
                        sim_threshold=0.80,
                    )
                    mouse_state.selected_feature = obj_feat
                    mouse_state.selected_bbox = s_bbox
                    mouse_state.selected_mask = s_mask
                    selection_bbox = s_bbox
                    selection_mask = s_mask

                elif mouse_state.selection_type == "drag":
                    if mouse_state.is_dragging and mouse_state.drag_start and mouse_state.drag_current:
                        xmin = min(mouse_state.drag_start[0], mouse_state.drag_current[0])
                        xmax = max(mouse_state.drag_start[0], mouse_state.drag_current[0])
                        ymin = min(mouse_state.drag_start[1], mouse_state.drag_current[1])
                        ymax = max(mouse_state.drag_start[1], mouse_state.drag_current[1])
                        selection_bbox = (ymin, xmin, ymax, xmax)
                    elif mouse_state.selected_bbox is not None:
                        selection_bbox = mouse_state.selected_bbox
                        roi_feat, _, _ = extractor.extract_from_bbox(pil_img, bbox_norm=selection_bbox)
                        mouse_state.selected_feature = roi_feat

            # 5. Spatial Multi-Object Detection across Patches
            detections = []
            if not is_calibrating and patch_tokens_spatial is not None:
                detections = visual_anchor_store.detect_objects_in_patches(
                    patch_tokens_grid=patch_tokens_spatial,
                    min_patch_similarity=0.78,
                    min_matching_patches=3,
                )

            # 6. Render Composite HUD with Heatmap, Bounding Boxes, and Mouse Selection
            composite_bgr, patch_rgb, telem = render_cozmo_frame_heatmap(
                raw_frame=calibrated_bgr,
                extractor=extractor,
                visualizer=visualizer,
                remind_engine=remind_engine,
                is_calibrating=is_calibrating,
                is_cozmo_cam=False,
                frame_count=frame_count,
                show_reticle=False,
                detections=detections,
                selection_bbox=selection_bbox,
                selection_mask=selection_mask,
            )

            disp_h, disp_w, _ = composite_bgr.shape

            # 7. Render Top Hardware Source & Telemetry Bar
            source_badge = "COZMO CAMERA" if is_cozmo_active else "WEBCAM"
            badge_color = (0, 200, 255) if is_cozmo_active else (255, 180, 0)
            src_str = f"SRC: {source_badge} (Press TAB/'V' to switch)"
            
            cv2.rectangle(composite_bgr, (disp_w - 380, 3), (disp_w - 10, 24), (20, 20, 20), -1)
            cv2.putText(
                composite_bgr,
                src_str,
                (disp_w - 372, 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.36,
                badge_color,
                1,
                cv2.LINE_AA,
            )

            # Render Cozmo Teleoperation & Lighting Sub-Bar
            light_badge = "ON" if cozmo_ctrl.headlight_on else "OFF"
            light_col = (0, 255, 255) if cozmo_ctrl.headlight_on else (180, 180, 180)
            v_bat = cozmo_ctrl.get_battery_voltage() if cozmo_ctrl.is_connected else 0.0

            tele_str = (
                f"Headlight: {light_badge} (O) | "
                f"Bright: {cozmo_ctrl.brightness_offset:+d} ([/]) | "
                f"Gamma: {cozmo_ctrl.gamma_val:.2f} (-/+) | "
                f"Head: {cozmo_ctrl.head_angle_deg:+.0f}° | "
                f"{v_bat:.2f}V"
            )
            cv2.rectangle(composite_bgr, (0, 27), (disp_w, 47), (25, 25, 25), -1)
            cv2.putText(
                composite_bgr,
                tele_str,
                (10, 42),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.36,
                (0, 255, 180),
                1,
                cv2.LINE_AA,
            )

            # Render Detection Summary Badge
            if detections:
                det_summary = f"RECOGNIZED: {', '.join([d['label'].upper() for d in detections])}"
                cv2.rectangle(composite_bgr, (10, disp_h - 65), (10 + len(det_summary) * 8 + 16, disp_h - 45), (0, 180, 0), -1)
                cv2.putText(
                    composite_bgr,
                    det_summary,
                    (18, disp_h - 51),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.40,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

            cv2.imshow(window_name, composite_bgr)

            # 8. Keyboard Controls & Hotkeys
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):
                break

            # Camera Switching (TAB or 'v')
            elif key in (9, ord('v'), ord('V')):
                if active_source == "webcam":
                    print(f"\n{CYAN}[Camera Source] Switching to Cozmo Camera...{RESET}")
                    if not cozmo_ctrl.is_connected:
                        if cozmo_ctrl.connect(timeout=8.0):
                            active_source = "cozmo"
                        else:
                            print(f"{YELLOW}[Camera Notice] Cozmo not reachable. Staying on webcam.{RESET}")
                    else:
                        active_source = "cozmo"
                else:
                    print(f"\n{CYAN}[Camera Source] Switching to Webcam...{RESET}")
                    if webcam_cap is None or not webcam_cap.isOpened():
                        webcam_cap = cv2.VideoCapture(0)
                        if not webcam_cap.isOpened():
                            webcam_cap = cv2.VideoCapture(1)
                    active_source = "webcam"

            # Camera Lighting & Brightness Controls
            elif key in (ord('o'), ord('O'), ord('p'), ord('P')):
                cozmo_ctrl.toggle_headlight()
            elif key in (ord(']'), ord('b')):
                cozmo_ctrl.adjust_brightness(+10)
            elif key in (ord('['), ord('B')):
                cozmo_ctrl.adjust_brightness(-10)
            elif key in (ord('+'), ord('=')):
                cozmo_ctrl.adjust_gamma(+0.10)
            elif key in (ord('-'), ord('_')):
                cozmo_ctrl.adjust_gamma(-0.10)
            elif key == ord('0'):
                cozmo_ctrl.reset_lighting()

            # Robot Teleoperation
            elif key in (ord('w'), ord('W')):
                cozmo_ctrl.drive_forward(55.0)
            elif key in (ord('s'), ord('S')):
                cozmo_ctrl.drive_backward(55.0)
            elif key in (ord('a'), ord('A')):
                cozmo_ctrl.turn_left(40.0)
            elif key in (ord('d'), ord('D')):
                cozmo_ctrl.turn_right(40.0)
            elif key in (ord(' '), ord('x'), ord('X')):
                cozmo_ctrl.stop_wheels()

            # Head Tilt Controls
            elif key in (ord('i'), ord('I')):
                cozmo_ctrl.tilt_head_up(5.0)
                print(f"{CYAN}[Head] Tilt Up -> {cozmo_ctrl.head_angle_deg:+.1f}°{RESET}")
            elif key in (ord('k'), ord('K')):
                cozmo_ctrl.tilt_head_down(5.0)
                print(f"{CYAN}[Head] Tilt Down -> {cozmo_ctrl.head_angle_deg:+.1f}°{RESET}")
            elif key in (ord('h'), ord('H')):
                cozmo_ctrl.set_head_angle(0.0)
                print(f"{CYAN}[Head] Reset to 0.0° (Horizontal){RESET}")

            # Lift Arm Controls
            elif key in (ord('u'), ord('U')):
                cozmo_ctrl.set_lift_height(cozmo_ctrl.lift_height_mm + 15.0)
            elif key in (ord('j'), ord('J')):
                cozmo_ctrl.set_lift_height(cozmo_ctrl.lift_height_mm - 15.0)

            # View Mode & Navigation
            elif key == ord('m'):
                new_mode = visualizer.cycle_view_mode()
                print(f"{CYAN}[View Mode] Switched to: {visualizer.VIEW_MODE_NAMES[new_mode]}{RESET}")
            elif key == ord('l'):
                print_anchor_table()
            elif key == ord('r'):
                extractor.recalibrate()
                frame_count = 0
                mouse_state.clear()
                print(f"{MAGENTA}[Recalibrate] PCA matrix reset.{RESET}")
            elif key == ord('c'):
                remind_engine.clear()
                mouse_state.clear()
                print(f"{YELLOW}[REMIND] Transient memory bank & selection cleared.{RESET}")

            # Teaching Mode
            elif key == ord('t'):
                print(f"\n{MAGENTA}{BOLD}[OBJECT TEACHING ACTIVATED]{RESET}")
                
                # Determine feature vector to teach
                if mouse_state.selected_feature is not None:
                    target_feat = mouse_state.selected_feature
                    source_desc = f"Mouse Click / Drag on {active_source.upper()}"
                else:
                    print(f"{YELLOW}💡 Tip: Click on the object in the camera feed to select it before pressing 't'!{RESET}")
                    print(f"{YELLOW}Extracting central visual region...{RESET}")
                    target_feat, _, _ = extractor.extract_reticle_roi(pil_img, reticle_box=(0.25, 0.25, 0.75, 0.75))
                    source_desc = f"Center Region on {active_source.upper()}"

                print(f"{YELLOW}Using {source_desc} (Pure object fingerprint, zero background/hands!){RESET}")
                print(f"{YELLOW}Enter label for this object (e.g. Charger, Me, CoffeeMug, Phone):{RESET}")
                try:
                    label_input = input(f"{BOLD}Object Label > {RESET}").strip()
                    if label_input:
                        anchor = remind_engine.teach_anchor(
                            label=label_input,
                            image_or_feat=target_feat,
                            x=0.0,
                            y=0.0,
                            is_permanent=True,
                            notes=f"Taught from {active_source.upper()} angle",
                        )
                        print(f"{GREEN}[SUCCESS] Pure fingerprint for '{label_input}' saved to visual_anchors.json!{RESET}\n")
                        mouse_state.clear()
                        print_anchor_table()
                    else:
                        print(f"{YELLOW}[Cancelled] Empty label provided.{RESET}")
                except Exception as err:
                    print(f"{RED}[Error teaching anchor] {err}{RESET}")

            elif key == ord('d'):
                print(f"\n{RED}[DELETE ANCHOR]{RESET}")
                label_to_del = input(f"{BOLD}Enter exact label to delete > {RESET}").strip()
                if visual_anchor_store.delete_anchor(label_to_del):
                    print(f"{GREEN}[SUCCESS] Deleted '{label_to_del}' from visual_anchors.json.{RESET}")
                    print_anchor_table()
                else:
                    print(f"{YELLOW}[Warning] Anchor '{label_to_del}' not found.{RESET}")

    except KeyboardInterrupt:
        pass
    finally:
        if cozmo_ctrl.is_connected:
            cozmo_ctrl.stop_wheels()
        if webcam_cap:
            webcam_cap.release()
        cv2.destroyAllWindows()
        print(f"\n{GREEN}[Demo Finished] All visual anchors preserved in visual_anchors.json.{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Moka AI - Interactive Object Teaching & Re-ID Demo")
    parser.add_argument("--source", type=str, default="webcam", choices=["webcam", "cozmo"], help="Initial camera input source")
    parser.add_argument("--model", type=str, default="dinov3", choices=["dinov3", "dinov2"], help="Vision backbone")
    args = parser.parse_args()

    run_interactive_teaching_demo(source=args.source, model_backend=args.model)
