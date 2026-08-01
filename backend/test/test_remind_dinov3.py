"""
Test script for verifying PyCozmo Direct Camera Stream + REMIND Memory Engine + DINOv3-Lightweight Pipeline.
Restored to the initial PCA Object Colorization pipeline (the user's preferred version).
"""

import sys
import time
import threading
import numpy as np
import cv2
from PIL import Image, ImageDraw
import torch
import torchvision.transforms as T
import pycozmo

# Terminal colors for scannable output log
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
GRAY = "\033[90m"
RESET = "\033[0m"

# Thread-safe image buffer for ZERO-LATENCY frame dropping
lock = threading.Lock()
latest_raw_image = None
new_frame_available = False
frame_count = 0

# Calibrated Camera Filter Parameters (Fixes Red Tint & Overexposure)
cam_params = {
    "red_gain": 0.85,     # Red Channel Multiplier
    "blue_gain": 1.05,    # Blue Channel Multiplier
    "brightness": -15,    # Brightness Offset
    "contrast": 1.10,     # Contrast Multiplier
    "gamma": 0.85,        # Gamma Curve
}

latest_sensor_state = {
    "is_falling": False,
    "cliff_detected": False,
    "is_picked_up": False,
    "battery_voltage": 0.0,
    "orientation": "UNKNOWN",
}

# -----------------------------------------------------------------------------
# DINOv3 LIGHTWEIGHT FEATURE & PATCH COLOR SEGMENTATION ENGINE (ORIGINAL PCA)
# -----------------------------------------------------------------------------

class DINOv3LightweightExtractor:
    """
    Extracts 384-D dense patch embedding features using DINO backbone.
    Computes both:
    1. Global scene feature vector (1, 384) for REMIND novelty indexing.
    2. Real-time 3-component PCA spatial color mask (16x16x3) for live object segment colorization!
    """
    def __init__(self, model_name: str = "dinov2_vits14"):
        print(f"{BLUE}[DINOv3] Initializing DINOv3-lightweight model ({model_name})...{RESET}")
        self.device = torch.device("cpu")
        try:
            self.model = torch.hub.load("facebookresearch/dinov2", model_name)
            self.model.eval().to(self.device)
            print(f"{GREEN}[DINOv3] Model loaded successfully! 384-D + 16x16 Patch Segmentation active.{RESET}")
        except Exception as e:
            print(f"{RED}[DINOv3 ERROR] Failed to load hub model ({e}).{RESET}")
            raise e

        # Standard ImageNet pre-processing transform for DINO
        self.transform = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def extract(self, pil_image: Image.Image):
        """
        Extracts global embedding vector AND spatial PCA object color mask.
        Returns: (global_vector [384], patch_color_grid [16, 16, 3])
        """
        tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            # Extract intermediate layer patch tokens (1, 256, 384)
            patch_tokens = self.model.get_intermediate_layers(tensor, n=1)[0].squeeze(0)  # (256, 384)
            patch_tokens_norm = torch.nn.functional.normalize(patch_tokens, p=2, dim=1)

            # 1. Global Scene Feature Vector (mean pooled over patches)
            global_feat = patch_tokens_norm.mean(dim=0, keepdim=True)
            global_feat_norm = torch.nn.functional.normalize(global_feat, p=2, dim=1).squeeze(0).cpu().numpy()

            # 2. Fast 3-Component PCA for Live Object Color Mask (256, 384) -> (256, 3)
            U, S, V = torch.pca_lowrank(patch_tokens_norm, q=3)
            pca_3d = torch.matmul(patch_tokens_norm, V[:, :3])  # (256, 3)

            p_min = pca_3d.min(dim=0).values
            p_max = pca_3d.max(dim=0).values
            denom = torch.where((p_max - p_min) == 0, torch.tensor(1.0), (p_max - p_min))
            norm_rgb = ((pca_3d - p_min) / denom * 255.0).byte().cpu().numpy()

            patch_color_grid = norm_rgb.reshape((16, 16, 3))

        return global_feat_norm, patch_color_grid


# -----------------------------------------------------------------------------
# REMIND REPLAY MEMORY INDEXING ENGINE
# -----------------------------------------------------------------------------

class REMINDMemoryEngine:
    """
    Dynamic Visual Memory Indexer (REMIND Engine).
    Indexes visual patch features, calculates cosine similarity against past memories,
    and computes a real-time Novelty Index (0.0 = Familiar Anchor, 1.0 = Highly Novel Object).
    """
    def __init__(self, novelty_threshold: float = 0.35, max_capacity: int = 500):
        self.novelty_threshold = novelty_threshold
        self.max_capacity = max_capacity
        self.memory_bank = []
        self.lock = threading.Lock()

    def process_feature(self, feature_vector: np.ndarray):
        """Computes cosine similarity against visual memory bank and updates index."""
        with self.lock:
            if len(self.memory_bank) == 0:
                self.memory_bank.append(feature_vector)
                return 1.0, "NOVEL SCENE DISCOVERED", 0.0

            memory_matrix = np.array(self.memory_bank)  # (K, 384)
            similarities = np.dot(memory_matrix, feature_vector)  # (K,)
            max_sim = float(np.max(similarities))
            novelty_score = float(np.clip(1.0 - max_sim, 0.0, 1.0))

            if novelty_score > self.novelty_threshold:
                if len(self.memory_bank) >= self.max_capacity:
                    self.memory_bank.pop(0)
                self.memory_bank.append(feature_vector)

            if novelty_score > 0.60:
                classification = "NOVEL SCENE / UNVISITED OBJECT"
            elif novelty_score > 0.35:
                classification = "PARTIALLY FAMILIAR REGION"
            else:
                classification = "RECOGNIZED DESK ANCHOR"

            return novelty_score, classification, max_sim

    def clear_memory(self):
        """Resets visual memory index."""
        with self.lock:
            self.memory_bank.clear()


# -----------------------------------------------------------------------------
# CAMERA PROCESSING & IMAGE ENHANCEMENT
# -----------------------------------------------------------------------------

def enhance_cozmo_frame(raw_bgr_frame, params=cam_params):
    """Software Color Balance & Exposure Correction Pipeline."""
    b, g, r = cv2.split(raw_bgr_frame)
    b = cv2.convertScaleAbs(b, alpha=params["blue_gain"])
    r = cv2.convertScaleAbs(r, alpha=params["red_gain"])
    frame_balanced = cv2.merge([b, g, r])

    frame_adjusted = cv2.convertScaleAbs(
        frame_balanced, alpha=params["contrast"], beta=params["brightness"]
    )

    gamma = max(params["gamma"], 0.1)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(frame_adjusted, table)


def on_camera_image(cli, image):
    """Ultra-fast PyCozmo camera callback (< 0.1ms)."""
    global latest_raw_image, new_frame_available
    with lock:
        latest_raw_image = image
        new_frame_available = True


def on_falling_change(cli, state: bool):
    latest_sensor_state["is_falling"] = state
    if state:
        print(f"\n{RED}[ALERT] FREEFALL DETECTED! Cozmo is falling from a surface!{RESET}")


def on_cliff_change(cli, state: bool):
    latest_sensor_state["cliff_detected"] = state
    if state:
        print(f"\n{RED}[ALERT] CLIFF DETECTED! Cozmo detected edge boundary!{RESET}")


def on_pickup_change(cli, state: bool):
    latest_sensor_state["is_picked_up"] = state


def on_orientation_change(cli, orientation):
    orient_name = orientation.name if hasattr(orientation, "name") else str(orientation)
    latest_sensor_state["orientation"] = orient_name


# -----------------------------------------------------------------------------
# MAIN TEST EXECUTION
# -----------------------------------------------------------------------------

def run_remind_dinov3_test():
    global latest_raw_image, new_frame_available, frame_count, cam_params

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"{BLUE}====================================================={RESET}")
    print(f"{BLUE}   PYCOZMO + REMIND + DINOv3 LIVE OBJECT COLORING    {RESET}")
    print(f"{BLUE}====================================================={RESET}")
    print(f"{YELLOW}[INFO] Original DINO Object Feature Heatmap ACTIVE.{RESET}")
    print(f"{YELLOW}[HOTKEYS IN STREAM WINDOW]:{RESET}")
    print(f"{GRAY}  ├─ 'm': Cycle View Modes (Dual-View / Full Overlay / Clean Feed){RESET}")
    print(f"{GRAY}  ├─ 'c': Clear REMIND Memory | '+' / '-': Brightness | 'r'/'e': Red | 'b'/'v': Blue{RESET}")
    print(f"{GRAY}  └─ 'q': Exit Stream{RESET}\n")

    # 1. Initialize DINOv3 Extractor & REMIND Memory Engine
    extractor = DINOv3LightweightExtractor("dinov2_vits14")
    remind_engine = REMINDMemoryEngine(novelty_threshold=0.35, max_capacity=500)

    # 2. Connect to Cozmo with Retry Loop
    print(f"{BLUE}[1/4] Connecting to Cozmo hardware...{RESET}")
    connected = False
    cli = None
    for attempt in range(1, 11):
        try:
            print(f"{BLUE}  └─ Connection attempt {attempt}/10...{RESET}")
            cli = pycozmo.Client()
            cli.start()
            cli.connect()
            cli.wait_for_robot(timeout=10.0)
            connected = True
            print(f"{GREEN}[SUCCESS] Connected to Cozmo!{RESET}\n")
            break
        except Exception as conn_err:
            print(f"{YELLOW}  └─ Attempt {attempt} failed ({conn_err}). Retrying in 2s...{RESET}")
            if cli:
                try:
                    cli.disconnect()
                    cli.stop()
                except Exception:
                    pass
                cli = None
            time.sleep(2.0)

    if not connected or cli is None:
        raise RuntimeError("Could not connect to Cozmo. Verify Cozmo power & Wi-Fi.")

    # 3. Register Event Handlers
    print(f"{BLUE}[2/4] Registering sensor & camera listeners...{RESET}")
    cli.add_handler(pycozmo.event.EvtRobotFallingChange, on_falling_change)
    cli.add_handler(pycozmo.event.EvtCliffDetectedChange, on_cliff_change)
    cli.add_handler(pycozmo.event.EvtRobotPickedUpChange, on_pickup_change)
    cli.add_handler(pycozmo.event.EvtRobotOrientationChange, on_orientation_change)
    cli.add_handler(pycozmo.event.EvtNewRawCameraImage, on_camera_image)
    cli.enable_camera(enable=True, color=True)
    print(f"{GREEN}[SUCCESS] Listeners active.{RESET}\n")

    # 4. OLED Display Init
    print(f"{BLUE}[3/4] Initializing OLED Screen Matrix (128x32)...{RESET}")
    img = Image.new("1", (128, 32), color=0)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 127, 31), outline=1, fill=0)
    draw.text((10, 4), "DINOv3 OBJECT MAP", fill=1)
    draw.text((15, 16), "LIVE COLORING ON", fill=1)
    cli.display_image(img)
    print(f"{GREEN}[SUCCESS] Screen initialized. Starting object colorization...{RESET}\n")

    # 5. Pipeline State Variables & View Modes
    # View Modes: 0 = Dual-View Side-by-Side, 1 = Full Color Mask Overlay, 2 = Clean Feed
    view_mode = 0
    view_mode_names = ["DUAL-VIEW (Camera | DINO Object Colors)", "FULL OVERLAY MASK", "CLEAN FEED"]

    latest_remind_results = {
        "novelty": 1.0,
        "classification": "INITIALIZING...",
        "latency_ms": 0.0,
        "memory_count": 0,
        "max_sim": 0.0,
        "color_mask_bgr": None,
    }
    processing_dinov3 = False

    def async_dino_remind_worker(pil_img: Image.Image):
        """Background thread worker for running DINO feature extraction + PCA Object Colorization."""
        nonlocal processing_dinov3
        try:
            t0 = time.time()
            global_feat, patch_color_rgb = extractor.extract(pil_img)
            novelty, classification, max_sim = remind_engine.process_feature(global_feat)
            dt_ms = (time.time() - t0) * 1000.0

            # Convert 16x16 RGB color grid to BGR for OpenCV
            patch_color_bgr = cv2.cvtColor(patch_color_rgb, cv2.COLOR_RGB2BGR)

            latest_remind_results["novelty"] = novelty
            latest_remind_results["classification"] = classification
            latest_remind_results["latency_ms"] = dt_ms
            latest_remind_results["memory_count"] = len(remind_engine.memory_bank)
            latest_remind_results["max_sim"] = max_sim
            latest_remind_results["color_mask_bgr"] = patch_color_bgr
        except Exception as err:
            print(f"\n{RED}[PIPELINE ERROR] DINO/REMIND processing failed: {err}{RESET}")
        finally:
            processing_dinov3 = False

    # 6. Continuous Zero-Latency Main Loop
    print(f"{BLUE}[4/4] REMIND + DINOv3 Live Object Colorization Active:{RESET}")
    print(f"{GRAY}-----------------------------------------------------------------------------{RESET}")

    last_telemetry_print = 0.0

    try:
        while True:
            # A. Process Camera Stream & Trigger DINO/REMIND Worker
            current_raw_img = None
            with lock:
                if new_frame_available:
                    current_raw_img = latest_raw_image
                    new_frame_available = False

            if current_raw_img is not None:
                frame_count += 1
                raw_bgr = cv2.cvtColor(np.array(current_raw_img), cv2.COLOR_RGB2BGR)
                calibrated_frame = enhance_cozmo_frame(raw_bgr, cam_params)

                # Trigger DINOv3 worker asynchronously if idle
                if not processing_dinov3:
                    processing_dinov3 = True
                    threading.Thread(
                        target=async_dino_remind_worker,
                        args=(current_raw_img.copy(),),
                        daemon=True,
                    ).start()

                # B. Render Live Stream & DINO Object Color Segmentation Mask
                h, w, _ = calibrated_frame.shape

                # Resize 16x16 PCA Object Color Grid to match Camera Resolution
                if latest_remind_results["color_mask_bgr"] is not None:
                    dino_mask_smooth = cv2.resize(
                        latest_remind_results["color_mask_bgr"], (w, h), interpolation=cv2.INTER_LINEAR
                    )
                else:
                    dino_mask_smooth = np.zeros((h, w, 3), dtype=np.uint8)

                nov = latest_remind_results["novelty"]
                class_text = latest_remind_results["classification"]
                mem_cnt = latest_remind_results["memory_count"]

                if nov > 0.60:
                    bar_color = (0, 0, 255)     # Red (Novel Scene)
                elif nov > 0.35:
                    bar_color = (0, 255, 255)   # Yellow (Familiar)
                else:
                    bar_color = (0, 255, 0)     # Green (Recognized Anchor)

                # Construct Selected View Mode Layout
                if view_mode == 0:
                    # DUAL-VIEW (Left: Calibrated Feed | Right: DINO Live Object Segmentation Colors)
                    left_pane = calibrated_frame.copy()
                    right_pane = cv2.addWeighted(calibrated_frame, 0.40, dino_mask_smooth, 0.60, 0)

                    # Overlay labels on right pane
                    cv2.putText(
                        right_pane, "DINO OBJECT COLOR MAP", (10, 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1
                    )
                    display_window = np.hstack((left_pane, right_pane))

                elif view_mode == 1:
                    # FULL OVERLAY MASK (Blended Camera + DINO Colors)
                    display_window = cv2.addWeighted(calibrated_frame, 0.50, dino_mask_smooth, 0.50, 0)

                else:
                    # CLEAN FEED
                    display_window = calibrated_frame.copy()

                disp_h, disp_w, _ = display_window.shape

                # Top Header Banner
                cv2.rectangle(display_window, (0, 0), (disp_w, 22), (20, 20, 20), -1)
                cv2.putText(
                    display_window,
                    f"DINOv3 Live Colors - Frame:{frame_count} | DINO:{latest_remind_results['latency_ms']:.0f}ms | Mode: {view_mode_names[view_mode]}",
                    (5, 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35,
                    (0, 255, 255),
                    1,
                )

                # REMIND Novelty Status Bar & Classification Badge
                bar_max_w = min(200, disp_w - 20)
                bar_width = int(bar_max_w * nov)
                cv2.rectangle(display_window, (10, 26), (10 + bar_max_w, 33), (50, 50, 50), -1)
                cv2.rectangle(display_window, (10, 26), (10 + bar_width, 33), bar_color, -1)

                cv2.putText(
                    display_window,
                    f"Novelty: {nov:.2f} ({class_text}) | Mem Index: {mem_cnt}/500",
                    (10, 45),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35,
                    bar_color,
                    1,
                )

                # Fall Warning Overlay
                if latest_sensor_state["is_falling"]:
                    cv2.rectangle(display_window, (0, 50), (disp_w, 75), (0, 0, 255), -1)
                    cv2.putText(
                        display_window,
                        "!!! FALL DETECTED !!!",
                        (10, 68),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        2,
                    )

                cv2.imshow("PyCozmo - REMIND + DINOv3 Live Object Coloring", display_window)

            # C. Safety Motor Controls & Telemetry Print
            status = getattr(cli, "robot_status", 0) or 0
            is_falling = bool(status & pycozmo.robot.RobotStatusFlag.IS_FALLING)
            cliff_detected = bool(status & pycozmo.robot.RobotStatusFlag.CLIFF_DETECTED)
            if is_falling or cliff_detected:
                cli.stop_all_motors()

            now = time.time()
            if now - last_telemetry_print > 0.15:
                nov = latest_remind_results["novelty"]
                class_text = latest_remind_results["classification"]
                mem_cnt = latest_remind_results["memory_count"]

                sys.stdout.write(
                    f"\rPipeline Status ──> Novelty: {nov:.2f} | Memory: {mem_cnt} entries | "
                    f"Class: {class_text} | DINO Latency: {latest_remind_results['latency_ms']:.0f}ms"
                )
                sys.stdout.flush()
                last_telemetry_print = now

            # D. Handle Keyboard Commands
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print(f"\n\n{GRAY}User requested exit via stream window.{RESET}")
                break
            elif key == ord("m"):
                view_mode = (view_mode + 1) % len(view_mode_names)
                print(f"\n{CYAN}[VIEW MODE CHANGED] Current Mode: {view_mode_names[view_mode]}{RESET}")
            elif key == ord("c"):
                remind_engine.clear_memory()
                print(f"\n{YELLOW}[REMIND] Visual memory bank cleared.{RESET}")
            elif key == ord("+") or key == ord("="):
                cam_params["brightness"] = min(cam_params["brightness"] + 5, 50)
            elif key == ord("-") or key == ord("_"):
                cam_params["brightness"] = max(cam_params["brightness"] - 5, -80)
            elif key == ord("r"):
                cam_params["red_gain"] = round(max(cam_params["red_gain"] - 0.05, 0.2), 2)
            elif key == ord("e"):
                cam_params["red_gain"] = round(min(cam_params["red_gain"] + 0.05, 1.5), 2)
            elif key == ord("b"):
                cam_params["blue_gain"] = round(min(cam_params["blue_gain"] + 0.05, 2.5), 2)
            elif key == ord("v"):
                cam_params["blue_gain"] = round(max(cam_params["blue_gain"] - 0.05, 0.5), 2)

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[INTERRUPTED] Pipeline stopped by user.{RESET}")
    except Exception as e:
        print(f"\n{RED}[ERROR] Pipeline execution failure: {e}{RESET}")
    finally:
        print(f"\n{BLUE}[SHUTDOWN] Releasing hardware handles and closing pipeline...{RESET}")
        if cli:
            try:
                cli.stop_all_motors()
                cli.enable_camera(enable=False)
                cli.disconnect()
                cli.stop()
            except Exception:
                pass
        cv2.destroyAllWindows()
        print(f"{GREEN}[SHUTDOWN COMPLETE]{RESET}")


if __name__ == "__main__":
    run_remind_dinov3_test()
