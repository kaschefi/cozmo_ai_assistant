import sys
import os
import time
import math
import cv2
import numpy as np
from PIL import Image

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Terminal formatting colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


class DINOPrecisionExtractor:
    """
    High-Precision Stabilized Feature & Patch Segmentation Heatmap Engine.
    Supports both DINOv3 (Hugging Face) and DINOv2 (TorchHub) with:
    1. Exact CLS + Register token stripping.
    2. Exact spatial grid height x width reconstruction (no distortion).
    3. Stabilized SVD Master Latent Space calibration across initial frames.
    4. Moving-average temporal smoothing for crisp, zero-flicker segmentation.
    """

    def __init__(
        self,
        backend: str = "dinov3",  # "dinov3" or "dinov2"
        calibration_frames: int = 15,
        target_size: int = 224,
    ):
        self.backend = backend.lower()
        self.calibration_target = calibration_frames
        self.target_size = target_size
        self.calibration_pool = []
        self.master_eigenvectors = None
        self.global_min = None
        self.global_max = None
        self.prev_mask = None
        self.alpha = 0.35  # Temporal smoothing moving average

        # Load Hugging Face access token from .env
        from dotenv import load_dotenv
        load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env")))
        load_dotenv()

        hf_token = (
            os.environ.get("HF_TOKEN")
            or os.environ.get("HUGGINGFACE_TOKEN")
            or os.environ.get("HUGGING_FACE_HUB_TOKEN")
            or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
            or os.environ.get("HUGGING_FACE_TOKEN")
        )

        if hf_token:
            os.environ["HF_TOKEN"] = hf_token
            try:
                from huggingface_hub import login
                login(token=hf_token, add_to_git_credential=False)
            except Exception:
                pass

        import torch
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"{BLUE}[DINO Engine] Initializing {BOLD}{self.backend.upper()}{RESET} on {BOLD}{str(self.device).upper()}{RESET}...")

        t0 = time.time()
        if self.backend == "dinov3":
            model_name = "facebook/dinov3-vits16-pretrain-lvd1689m"
            from transformers import AutoImageProcessor, AutoModel
            self.processor = AutoImageProcessor.from_pretrained(model_name, token=hf_token)
            self.model = AutoModel.from_pretrained(
                model_name,
                device_map="auto" if torch.cuda.is_available() else None,
                token=hf_token,
            )
            if not torch.cuda.is_available():
                self.model = self.model.to(self.device)
            self.model.eval()
            self.patch_size = 16
        else:
            # DINOv2 TorchHub
            model_name = "dinov2_vits14"
            self.model = torch.hub.load("facebookresearch/dinov2", model_name)
            self.model.eval().to(self.device)
            import torchvision.transforms as T
            self.transform = T.Compose([
                T.Resize((self.target_size, self.target_size)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            self.patch_size = 14

        print(f"{GREEN}[DINO Engine] {self.backend.upper()} loaded in {time.time() - t0:.2f}s! (Patch Size: {self.patch_size}){RESET}")

    def extract(self, pil_image: Image.Image, is_calibrating: bool = False):
        import torch

        if self.backend == "dinov3":
            # Force square resolution to match patch grid exactly
            resized_pil = pil_image.resize((self.target_size, self.target_size), Image.BILINEAR)
            inputs = self.processor(images=resized_pil, return_tensors="pt")
            if self.device.type == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)
                tokens = outputs.last_hidden_state.squeeze(0)  # (total_tokens, 384)

                # DINOv3 tokens: [CLS] (1) + optional [REGISTERS] (usually 4) + Patches (NxN)
                num_tokens = tokens.shape[0]
                expected_patches = (self.target_size // self.patch_size) ** 2  # (224/16)^2 = 14*14 = 196
                num_special_tokens = num_tokens - expected_patches

                if num_special_tokens > 0:
                    patch_tokens = tokens[num_special_tokens:]  # Strip CLS + all register tokens!
                else:
                    patch_tokens = tokens

                grid_h = self.target_size // self.patch_size  # 14
                grid_w = self.target_size // self.patch_size  # 14

        else:
            # DINOv2 Pipeline
            tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                patch_tokens = self.model.get_intermediate_layers(tensor, n=1)[0].squeeze(0)  # (256, 384)
                grid_h = self.target_size // self.patch_size  # 16
                grid_w = self.target_size // self.patch_size  # 16

        patch_tokens_norm = torch.nn.functional.normalize(patch_tokens, p=2, dim=1)

        # Global image descriptor for novelty
        global_feat = patch_tokens_norm.mean(dim=0, keepdim=True)
        global_feat_norm = torch.nn.functional.normalize(global_feat, p=2, dim=1).squeeze(0).cpu().numpy()

        # --- PHASE 1: CALIBRATION ---
        if is_calibrating:
            self.calibration_pool.append(patch_tokens_norm.cpu().numpy())
            return global_feat_norm, np.zeros((grid_h, grid_w, 3), dtype=np.uint8)

        # --- PHASE 2: SVD MASTER LATENT SPACE FIT ---
        if self.master_eigenvectors is None:
            print(f"\n{MAGENTA}[CALIBRATION COMPLETE] Fitting Master PCA Subspace over {len(self.calibration_pool)} frames...{RESET}")
            if len(self.calibration_pool) > 0:
                combined_pool = np.vstack(self.calibration_pool)
            else:
                combined_pool = patch_tokens_norm.cpu().numpy()

            mean_centered = combined_pool - np.mean(combined_pool, axis=0)
            _, _, Vh = np.linalg.svd(mean_centered, full_matrices=False)
            self.master_eigenvectors = Vh[:3, :].T  # (dim, 3)

            for i in range(3):
                max_abs_idx = np.argmax(np.abs(self.master_eigenvectors[:, i]))
                if self.master_eigenvectors[max_abs_idx, i] < 0:
                    self.master_eigenvectors[:, i] = -self.master_eigenvectors[:, i]

            projected_pool = np.dot(combined_pool, self.master_eigenvectors)
            self.global_min = projected_pool.min(axis=0)
            self.global_max = projected_pool.max(axis=0)
            print(f"{GREEN}[SYSTEM LOCK] Master PCA bounds locked down. Zero-flicker space established.{RESET}")

        # --- PHASE 3: RUN STABILIZED INFERENCE ---
        current_tokens = patch_tokens_norm.cpu().numpy()
        pca_3d = np.dot(current_tokens, self.master_eigenvectors)

        denom = np.where((self.global_max - self.global_min) == 0, 1.0, (self.global_max - self.global_min))
        norm_rgb = np.clip(((pca_3d - self.global_min) / denom) * 255.0, 0, 255).astype(np.uint8)

        patch_color_grid = norm_rgb.reshape((grid_h, grid_w, 3))

        if self.prev_mask is not None and self.prev_mask.shape == patch_color_grid.shape:
            patch_color_grid = (self.alpha * patch_color_grid + (1.0 - self.alpha) * self.prev_mask).astype(np.uint8)
        self.prev_mask = patch_color_grid

        return global_feat_norm, patch_color_grid


class REMINDMemoryBank:
    """Lightweight real-time visual memory bank and novelty evaluator."""
    def __init__(self, novelty_threshold: float = 0.35, max_capacity: int = 500):
        self.novelty_threshold = novelty_threshold
        self.max_capacity = max_capacity
        self.memory_bank = []
        self.total_objects_found = 0

    def process_feature(self, feature_vector: np.ndarray):
        if len(self.memory_bank) == 0:
            self.memory_bank.append(feature_vector)
            self.total_objects_found += 1
            return 1.0, "ESTABLISHING ANCHOR", 0.0, True

        memory_matrix = np.array(self.memory_bank)
        similarities = np.dot(memory_matrix, feature_vector)
        max_sim = float(np.max(similarities))
        novelty_score = float(np.clip(1.0 - max_sim, 0.0, 1.0))

        stored_new = False
        if novelty_score > self.novelty_threshold:
            if len(self.memory_bank) >= self.max_capacity:
                self.memory_bank.pop(0)
            self.memory_bank.append(feature_vector)
            self.total_objects_found += 1
            stored_new = True

        if novelty_score > 0.60:
            classification = "NOVEL OBJECT"
        elif novelty_score > 0.35:
            classification = "PARTIALLY FAMILIAR"
        else:
            classification = "FAMILIAR ANCHOR"

        return novelty_score, classification, max_sim, stored_new

    def clear_memory(self):
        self.memory_bank.clear()


def run_precision_webcam_test(initial_backend: str = "dinov3"):
    print(f"\n{CYAN}{'='*75}{RESET}")
    print(f"{CYAN}{BOLD}   MOKA AI ASSISTANT -- PRECISION DINO WEBCAM FEATURE HEATMAP   {RESET}")
    print(f"{CYAN}{'='*75}{RESET}\n")

    current_backend = initial_backend
    try:
        extractor = DINOPrecisionExtractor(backend=current_backend, calibration_frames=15)
    except Exception as e:
        print(f"{RED}[Error loading {current_backend}] {e}. Falling back to DINOv2...{RESET}")
        current_backend = "dinov2"
        extractor = DINOPrecisionExtractor(backend=current_backend, calibration_frames=15)

    remind_engine = REMINDMemoryBank()

    print(f"\n{BLUE}[Camera] Opening Webcam (index 0)...{RESET}")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print(f"{RED}[FAIL] No webcam accessible.{RESET}")
            return False

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print(f"{GREEN}[OK] Webcam connected!{RESET}")

    print(f"\n{YELLOW}Controls:{RESET}")
    print(f"  - Press {BOLD}'q'{RESET} to exit")
    print(f"  - Press {BOLD}'m'{RESET} to cycle View Mode (Dual-View -> Blended -> Heatmap-Only)")
    print(f"  - Press {BOLD}'b'{RESET} to toggle Backend Model ({BOLD}DINOv3 <-> DINOv2{RESET})")
    print(f"  - Press {BOLD}'c'{RESET} to clear REMIND memory bank")
    print(f"  - Press {BOLD}'r'{RESET} to recalibrate Master PCA Space\n")

    view_mode = 0
    view_modes = ["DUAL-VIEW INTERFACE", "BLENDED OVERLAY", "HEATMAP-ONLY", "CLEAN FEED"]
    frame_count = 0

    while True:
        ret, frame_bgr = cap.read()
        if not ret or frame_bgr is None:
            time.sleep(0.01)
            continue

        frame_count += 1
        h, w, _ = frame_bgr.shape
        is_calibrating = frame_count <= extractor.calibration_target

        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)

        t0 = time.time()
        global_feat, patch_color_rgb = extractor.extract(pil_img, is_calibrating=is_calibrating)
        latency_ms = (time.time() - t0) * 1000.0

        if not is_calibrating:
            novelty, classification, max_sim, stored_new = remind_engine.process_feature(global_feat)
            patch_color_bgr = cv2.cvtColor(patch_color_rgb, cv2.COLOR_RGB2BGR)
            # High quality bicubic upscaling for smooth crisp heatmap boundaries
            smooth_mask = cv2.resize(patch_color_bgr, (w, h), interpolation=cv2.INTER_CUBIC)

            if stored_new:
                print(f"\n{GREEN}[REMIND] Stored new object! Total in bank: {len(remind_engine.memory_bank)}{RESET}")
        else:
            novelty, classification, stored_new = 1.0, f"CALIBRATING RETINAL MATRIX ({frame_count}/{extractor.calibration_target})...", False
            smooth_mask = np.zeros((h, w, 3), dtype=np.uint8)

        # Build View
        if view_mode == 0:
            left_pane = frame_bgr.copy()
            right_pane = cv2.addWeighted(frame_bgr, 0.25, smooth_mask, 0.75, 0) if not is_calibrating else frame_bgr.copy()
            if is_calibrating:
                cv2.putText(right_pane, f"CALIBRATING SPACE: {frame_count}/{extractor.calibration_target}",
                            (30, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2, cv2.LINE_AA)
            display_window = np.hstack((left_pane, right_pane))
        elif view_mode == 1:
            display_window = cv2.addWeighted(frame_bgr, 0.40, smooth_mask, 0.60, 0) if not is_calibrating else frame_bgr.copy()
        elif view_mode == 2:
            display_window = smooth_mask.copy() if not is_calibrating else frame_bgr.copy()
        else:
            display_window = frame_bgr.copy()

        disp_h, disp_w, _ = display_window.shape

        # Top Display Strip
        cv2.rectangle(display_window, (0, 0), (disp_w, 28), (15, 15, 15), -1)
        cv2.putText(
            display_window,
            f"Moka Core ── Model: {extractor.backend.upper()} | Frame: {frame_count} | Mode: {view_modes[view_mode]} | Latency: {latency_ms:.0f}ms",
            (12, 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 200),
            1,
            cv2.LINE_AA,
        )

        # Bottom Analytics Strip
        bar_color = (0, 165, 255) if is_calibrating else (
            (0, 0, 255) if novelty > 0.60 else ((0, 255, 255) if novelty > 0.35 else (0, 255, 0)))
        bar_max_w = 220
        bar_width = int(bar_max_w * novelty)

        cv2.rectangle(display_window, (20, disp_h - 45), (20 + bar_max_w, disp_h - 35), (45, 45, 45), -1)
        cv2.rectangle(display_window, (20, disp_h - 45), (20 + bar_width, disp_h - 35), bar_color, -1)

        cv2.putText(
            display_window,
            f"Novelty: {novelty:.2f} ({classification}) | Active Bank: {len(remind_engine.memory_bank)}/500 | Total Stored: {remind_engine.total_objects_found}",
            (20, disp_h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            bar_color,
            1,
            cv2.LINE_AA,
        )

        cv2.imshow("Moka AI - High Precision DINO Feature Heatmap", display_window)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key == ord('m'):
            view_mode = (view_mode + 1) % len(view_modes)
        elif key == ord('b'):
            # Toggle Backend DINOv3 <-> DINOv2
            new_backend = "dinov2" if current_backend == "dinov3" else "dinov3"
            print(f"\n{YELLOW}[Switching Model] Reloading backend to {new_backend.upper()}...{RESET}")
            try:
                extractor = DINOPrecisionExtractor(backend=new_backend, calibration_frames=15)
                current_backend = new_backend
                frame_count = 0
            except Exception as e:
                print(f"{RED}[Switch Failed] {e}{RESET}")
        elif key == ord('r'):
            # Recalibrate PCA
            extractor.master_eigenvectors = None
            extractor.calibration_pool = []
            frame_count = 0
            print(f"\n{MAGENTA}[Recalibration] Triggered fresh PCA baseline calibration.{RESET}")
        elif key == ord('c'):
            remind_engine.clear_memory()
            print(f"\n{YELLOW}[REMIND] Visual memory bank cleared.{RESET}")

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n{GREEN}[SUCCESS] Precision Heatmap Session Finished.{RESET}\n")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="dinov3", choices=["dinov3", "dinov2"], help="Vision backbone")
    args = parser.parse_args()
    run_precision_webcam_test(initial_backend=args.model)
