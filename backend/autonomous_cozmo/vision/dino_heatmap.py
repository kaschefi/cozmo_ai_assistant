"""
Moka AI Assistant - Autonomous Cozmo Vision Subsystem
High-Precision Stabilized Feature & Patch Segmentation Heatmap Engine (DINOv3 / DINOv2).

Provides:
1. DINOPrecisionExtractor: High-precision feature extractor with SVD Master Latent Space calibration,
   exact CLS + register token stripping, and moving-average temporal smoothing for zero-flicker heatmaps.
2. enhance_cozmo_frame: Software color balance (red/blue gain), contrast, brightness, and gamma correction
   calibrated specifically for Cozmo's hardware camera.
3. DINOHeatmapVisualizer: Multi-layout HUD composite renderer (Dual-View, Blended Overlay, Heatmap-Only, Clean Feed)
   with real-time REMIND novelty metrics and hardware safety alerts.
4. render_cozmo_frame_heatmap: One-call frame processing and heatmap rendering pipeline.
"""

import os
import sys
import time
import math
import threading
from typing import Optional, Tuple, Dict, Any, Union, List
import numpy as np
from PIL import Image
import cv2

# Terminal formatting colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Default Cozmo Hardware Camera Calibration Filter Parameters
DEFAULT_COZMO_CAM_PARAMS = {
    "red_gain": 0.85,     # Red Channel Multiplier (compensates for Cozmo sensor warm tint)
    "blue_gain": 1.05,    # Blue Channel Multiplier
    "brightness": -15,    # Brightness Offset (reduces sensor glare)
    "contrast": 1.10,     # Contrast Multiplier
    "gamma": 0.85,        # Gamma Curve (< 1.0 brightens shadows cleanly)
}


def enhance_cozmo_frame(
    raw_bgr_frame: np.ndarray,
    params: Optional[Dict[str, float]] = None,
) -> np.ndarray:
    """
    Software Color Balance & Exposure Correction Pipeline calibrated for Cozmo's Camera.
    Eliminates heavy red tint, balances blue channels, and normalizes dynamic range.
    """
    p = params or DEFAULT_COZMO_CAM_PARAMS
    b, g, r = cv2.split(raw_bgr_frame)
    b = cv2.convertScaleAbs(b, alpha=p.get("blue_gain", 1.05))
    r = cv2.convertScaleAbs(r, alpha=p.get("red_gain", 0.85))
    frame_balanced = cv2.merge([b, g, r])

    frame_adjusted = cv2.convertScaleAbs(
        frame_balanced,
        alpha=p.get("contrast", 1.10),
        beta=p.get("brightness", -15),
    )

    gamma = max(p.get("gamma", 0.85), 0.1)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(frame_adjusted, table)


class DINOPrecisionExtractor:
    """
    High-Precision Stabilized Feature & Patch Segmentation Heatmap Engine.
    Supports both DINOv3 (Hugging Face) and DINOv2 (TorchHub) with:
    1. Exact CLS + Register token stripping (retains only true spatial patch embeddings).
    2. Exact spatial grid height x width reconstruction (no distortion).
    3. Stabilized SVD Master Latent Space calibration across initial frames (locks PCA axes without color inversion).
    4. Moving-average temporal smoothing for crisp, zero-flicker semantic segmentation.
    5. Returns both L2-normalized global vector for REMIND and (grid_h, grid_w, 3) RGB patch color heatmap.
    """

    DEFAULT_DINOV3_MODEL = "facebook/dinov3-vits16-pretrain-lvd1689m"
    DEFAULT_DINOV2_MODEL = "dinov2_vits14"

    def __init__(
        self,
        backend: str = "dinov3",  # "dinov3" or "dinov2"
        calibration_frames: int = 15,
        target_size: int = 224,
        alpha: float = 0.35,
        lazy_init: bool = False,
    ):
        self.backend = backend.lower()
        self.calibration_target = max(1, calibration_frames)
        self.target_size = target_size
        self.alpha = float(alpha)
        self.calibration_pool: List[np.ndarray] = []
        self.master_eigenvectors: Optional[np.ndarray] = None
        self.global_min: Optional[np.ndarray] = None
        self.global_max: Optional[np.ndarray] = None
        self.prev_mask: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._initialized = False

        self.model = None
        self.processor = None
        self.transform = None
        self.device = None
        self.patch_size = 16 if self.backend == "dinov3" else 14
        self.is_mock = False

        if not lazy_init:
            self._init_model()

    def _init_model(self):
        if self._initialized:
            return
        self._initialized = True

        if os.environ.get("DINO_OFFLINE") == "1":
            print(f"{YELLOW}[DINO Heatmap] DINO_OFFLINE requested -> Running lightweight fallback.{RESET}")
            self.is_mock = True
            return

        # Load Hugging Face access token from .env
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env")))
            load_dotenv()
        except Exception:
            pass

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

        try:
            import torch
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            print(f"{BLUE}[DINO Heatmap] Initializing {BOLD}{self.backend.upper()}{RESET} on {BOLD}{str(self.device).upper()}{RESET}...")

            t0 = time.time()
            if self.backend == "dinov3":
                model_name = self.DEFAULT_DINOV3_MODEL
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
                model_name = self.DEFAULT_DINOV2_MODEL
                self.model = torch.hub.load("facebookresearch/dinov2", model_name)
                self.model.eval().to(self.device)
                import torchvision.transforms as T
                self.transform = T.Compose([
                    T.Resize((self.target_size, self.target_size)),
                    T.ToTensor(),
                    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ])
                self.patch_size = 14

            print(f"{GREEN}[DINO Heatmap] {self.backend.upper()} loaded in {time.time() - t0:.2f}s! (Patch Size: {self.patch_size}){RESET}")
        except Exception as e:
            print(f"{YELLOW}[DINO Heatmap] Primary model init failed ({e}). Attempting DINOv2 fallback...{RESET}")
            try:
                import torch
                self.backend = "dinov2"
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                model_name = self.DEFAULT_DINOV2_MODEL
                self.model = torch.hub.load("facebookresearch/dinov2", model_name)
                self.model.eval().to(self.device)
                import torchvision.transforms as T
                self.transform = T.Compose([
                    T.Resize((self.target_size, self.target_size)),
                    T.ToTensor(),
                    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
                ])
                self.patch_size = 14
                print(f"{GREEN}[DINO Heatmap] DINOv2 fallback loaded successfully on {self.device}!{RESET}")
            except Exception as e2:
                print(f"{RED}[DINO Heatmap] Model loading failed ({e2}). Using mock visual engine.{RESET}")
                self.is_mock = True

    def extract_dense(
        self,
        image_input: Union[Image.Image, np.ndarray],
        is_calibrating: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extracts global scene descriptor vector, stabilized spatial patch color heatmap,
        and spatial patch token embeddings (grid_h, grid_w, 384).
        Returns: (global_feat_norm, patch_color_grid, patch_tokens_spatial)
        """

        if not self._initialized:
            self._init_model()

        # Normalize input to PIL Image RGB
        if isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 2:
                rgb_array = cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB)
            elif image_input.shape[2] == 4:
                rgb_array = cv2.cvtColor(image_input, cv2.COLOR_BGRA2RGB)
            elif image_input.shape[2] == 3:
                # Assume BGR if coming from OpenCV numpy
                rgb_array = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            else:
                rgb_array = image_input
            pil_image = Image.fromarray(rgb_array)
        else:
            pil_image = image_input.convert("RGB")

        with self._lock:
            if self.is_mock:
                return self._extract_fallback(pil_image, is_calibrating)

            try:
                import torch

                grid_h = self.target_size // self.patch_size
                grid_w = self.target_size // self.patch_size

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
                        expected_patches = grid_h * grid_w
                        num_special_tokens = num_tokens - expected_patches

                        if num_special_tokens > 0:
                            patch_tokens = tokens[num_special_tokens:]  # Strip CLS + all register tokens!
                        else:
                            patch_tokens = tokens

                else:
                    # DINOv2 Pipeline
                    tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
                    with torch.no_grad():
                        patch_tokens = self.model.get_intermediate_layers(tensor, n=1)[0].squeeze(0)  # (256, 384)

                patch_tokens_norm = torch.nn.functional.normalize(patch_tokens, p=2, dim=1)

                # Global image descriptor for novelty
                global_feat = patch_tokens_norm.mean(dim=0, keepdim=True)
                global_feat_norm = torch.nn.functional.normalize(global_feat, p=2, dim=1).squeeze(0).cpu().numpy().astype(np.float32)

                # --- PHASE 1: CALIBRATION ---
                if is_calibrating:
                    self.calibration_pool.append(patch_tokens_norm.cpu().numpy())
                    spatial_tokens = patch_tokens_norm.cpu().numpy().reshape((grid_h, grid_w, -1))
                    return global_feat_norm, np.zeros((grid_h, grid_w, 3), dtype=np.uint8), spatial_tokens


                # --- PHASE 2: SVD MASTER LATENT SPACE FIT ---
                if self.master_eigenvectors is None:
                    if len(self.calibration_pool) > 0:
                        combined_pool = np.vstack(self.calibration_pool)
                    else:
                        combined_pool = patch_tokens_norm.cpu().numpy()

                    mean_centered = combined_pool - np.mean(combined_pool, axis=0)
                    _, _, Vh = np.linalg.svd(mean_centered, full_matrices=False)
                    self.master_eigenvectors = Vh[:3, :].T  # (dim, 3)

                    # Ensure consistent sign orientation to prevent arbitrary color inversion
                    for i in range(3):
                        max_abs_idx = np.argmax(np.abs(self.master_eigenvectors[:, i]))
                        if self.master_eigenvectors[max_abs_idx, i] < 0:
                            self.master_eigenvectors[:, i] = -self.master_eigenvectors[:, i]

                    projected_pool = np.dot(combined_pool, self.master_eigenvectors)
                    self.global_min = projected_pool.min(axis=0)
                    self.global_max = projected_pool.max(axis=0)

                # --- PHASE 3: RUN STABILIZED INFERENCE ---
                current_tokens = patch_tokens_norm.cpu().numpy()
                pca_3d = np.dot(current_tokens, self.master_eigenvectors)

                denom = np.where((self.global_max - self.global_min) == 0, 1.0, (self.global_max - self.global_min))
                norm_rgb = np.clip(((pca_3d - self.global_min) / denom) * 255.0, 0, 255).astype(np.uint8)

                patch_color_grid = norm_rgb.reshape((grid_h, grid_w, 3))

                if self.prev_mask is not None and self.prev_mask.shape == patch_color_grid.shape:
                    patch_color_grid = (self.alpha * patch_color_grid + (1.0 - self.alpha) * self.prev_mask).astype(np.uint8)
                self.prev_mask = patch_color_grid

                patch_tokens_spatial = patch_tokens_norm.cpu().numpy().reshape((grid_h, grid_w, -1))
                return global_feat_norm, patch_color_grid, patch_tokens_spatial

            except Exception as e:
                print(f"{RED}[DINO Heatmap Error] Extraction failed: {e}. Using fallback.{RESET}")
                return self._extract_fallback(pil_image, is_calibrating)

    def extract(
        self,
        image_input: Union[Image.Image, np.ndarray],
        is_calibrating: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts global descriptor and patch color grid.
        Returns: (global_feat_norm, patch_color_grid)
        """
        res = self.extract_dense(image_input, is_calibrating=is_calibrating)
        return res[0], res[1]

    def extract_reticle_roi(
        self,
        image_input: Union[Image.Image, np.ndarray],
        reticle_box: Tuple[float, float, float, float] = (0.25, 0.25, 0.75, 0.75),
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extracts pure object embedding strictly from within the normalized reticle ROI [ymin, xmin, ymax, xmax].
        Completely excludes surrounding background pixels/tokens from the vector!
        Returns: (roi_feat_norm, patch_color_grid, patch_tokens_spatial)
        """
        global_feat, patch_color, patch_tokens = self.extract_dense(image_input, is_calibrating=False)
        grid_h, grid_w, dim = patch_tokens.shape

        ymin, xmin, ymax, xmax = reticle_box
        r_min = max(0, int(ymin * grid_h))
        r_max = min(grid_h, max(r_min + 1, int(ymax * grid_h)))
        c_min = max(0, int(xmin * grid_w))
        c_max = min(grid_w, max(c_min + 1, int(xmax * grid_w)))

        roi_tokens = patch_tokens[r_min:r_max, c_min:c_max, :].reshape(-1, dim)
        if len(roi_tokens) > 0:
            roi_mean = np.mean(roi_tokens, axis=0)
            norm = np.linalg.norm(roi_mean)
            roi_feat_norm = (roi_mean / norm).astype(np.float32) if norm > 1e-6 else roi_mean.astype(np.float32)
        else:
            roi_feat_norm = global_feat

        return roi_feat_norm, patch_color, patch_tokens

    def extract_from_click_segment(
        self,
        image_input: Union[Image.Image, np.ndarray],
        click_norm_x: float,
        click_norm_y: float,
        sim_threshold: float = 0.80,
    ) -> Tuple[np.ndarray, Tuple[float, float, float, float], np.ndarray, np.ndarray]:
        """
        Extracts pure object embedding by clicking directly on the object.
        Segments the contiguous patch cluster belonging to the clicked object,
        completely isolating it from hands, fingers, and background!
        Returns:
            (object_feat_norm, (ymin, xmin, ymax, xmax), patch_color_grid, object_mask)
        """
        global_feat, patch_color, patch_tokens = self.extract_dense(image_input, is_calibrating=False)
        grid_h, grid_w, dim = patch_tokens.shape

        r0 = min(grid_h - 1, max(0, int(click_norm_y * grid_h)))
        c0 = min(grid_w - 1, max(0, int(click_norm_x * grid_w)))

        seed_token = patch_tokens[r0, c0, :]
        sim_map = np.dot(patch_tokens, seed_token)

        binary_mask = (sim_map >= sim_threshold).astype(np.uint8)
        num_labels, labels = cv2.connectedComponents(binary_mask)
        click_label = labels[r0, c0]
        if click_label > 0:
            object_mask = (labels == click_label)

        else:
            object_mask = np.zeros((grid_h, grid_w), dtype=bool)
            object_mask[r0, c0] = True

        coords = np.argwhere(object_mask)
        ymin = float(coords[:, 0].min() / grid_h)
        xmin = float(coords[:, 1].min() / grid_w)
        ymax = float((coords[:, 0].max() + 1) / grid_h)
        xmax = float((coords[:, 1].max() + 1) / grid_w)

        obj_tokens = patch_tokens[object_mask]
        obj_mean = np.mean(obj_tokens, axis=0)
        norm = np.linalg.norm(obj_mean)
        obj_feat_norm = (obj_mean / norm).astype(np.float32) if norm > 1e-6 else obj_mean.astype(np.float32)

        return obj_feat_norm, (ymin, xmin, ymax, xmax), patch_color, object_mask

    def extract_from_bbox(
        self,
        image_input: Union[Image.Image, np.ndarray],
        bbox_norm: Tuple[float, float, float, float],
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extracts pure object embedding strictly from within a custom user-dragged bounding box.
        Returns: (roi_feat_norm, patch_color_grid, patch_tokens_spatial)
        """
        return self.extract_reticle_roi(image_input, reticle_box=bbox_norm)

    def _extract_fallback(self, pil_image: Image.Image, is_calibrating: bool) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:

        """Fast fallback generator producing a simulated spatial heatmap and feature vector."""
        grid_dim = self.target_size // self.patch_size
        resized = pil_image.resize((grid_dim, grid_dim)).convert("RGB")
        patch_grid = np.array(resized, dtype=np.uint8)

        # Generate 384-D color histogram vector
        arr = patch_grid.astype(np.float32) / 255.0
        h_flat = arr.reshape(-1)
        feat_vec = np.zeros(384, dtype=np.float32)
        take_len = min(len(h_flat), 384)
        feat_vec[:take_len] = h_flat[:take_len]
        norm = np.linalg.norm(feat_vec)
        if norm > 1e-6:
            feat_vec /= norm

        dense_spatial = np.tile(feat_vec, (grid_dim, grid_dim, 1))

        if is_calibrating:
            return feat_vec, np.zeros((grid_dim, grid_dim, 3), dtype=np.uint8), dense_spatial
        return feat_vec, patch_grid, dense_spatial

    def recalibrate(self):
        """Resets the Master PCA calibration space and starts fresh accumulation."""
        with self._lock:
            self.master_eigenvectors = None
            self.calibration_pool.clear()
            self.global_min = None
            self.global_max = None
            self.prev_mask = None


class DINOHeatmapVisualizer:

    """
    Renders modern, high-contrast composite visualization interfaces for Cozmo's camera feed.
    Supports Dual-View (Side-by-Side), Blended Heatmap Overlay, Heatmap-Only, and Clean Feed.
    Includes HUD analytics for REMIND memory status, novelty metrics, and hardware alerts.
    """

    VIEW_DUAL = 0
    VIEW_BLENDED = 1
    VIEW_HEATMAP_ONLY = 2
    VIEW_CLEAN_FEED = 3

    VIEW_MODE_NAMES = [
        "DUAL-VIEW INTERFACE",
        "BLENDED OVERLAY",
        "HEATMAP-ONLY",
        "CLEAN FEED",
    ]

    def __init__(
        self,
        default_view_mode: int = VIEW_DUAL,
        heatmap_weight: float = 0.65,
        camera_weight: float = 0.35,
    ):
        self.view_mode = default_view_mode
        self.heatmap_weight = heatmap_weight
        self.camera_weight = camera_weight

    def cycle_view_mode(self) -> int:
        """Cycles to the next visual layout mode."""
        self.view_mode = (self.view_mode + 1) % len(self.VIEW_MODE_NAMES)
        return self.view_mode

    def render_composite(
        self,
        frame_bgr: np.ndarray,
        patch_color_rgb: np.ndarray,
        is_calibrating: bool = False,
        calibration_progress: Tuple[int, int] = (15, 15),
        novelty_score: float = 0.0,
        classification: str = "FAMILIAR ANCHOR",
        active_memories: int = 0,
        max_memories: int = 500,
        total_objects: int = 0,
        latency_ms: float = 0.0,
        model_name: str = "DINOV3",
        frame_count: int = 0,
        alert_text: Optional[str] = None,
        view_mode: Optional[int] = None,
        show_reticle: bool = False,
        reticle_box: Tuple[float, float, float, float] = (0.25, 0.25, 0.75, 0.75),
        detections: Optional[List[Dict[str, Any]]] = None,
        selection_bbox: Optional[Tuple[float, float, float, float]] = None,
        selection_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:



        """
        Builds the composite UI layout based on active view mode with HUD analytics overlay.
        """
        mode = self.view_mode if view_mode is None else view_mode
        h, w, _ = frame_bgr.shape

        # Upscale low-res patch color grid to match camera frame resolution
        if patch_color_rgb is not None and patch_color_rgb.size > 0 and not is_calibrating:
            patch_color_bgr = cv2.cvtColor(patch_color_rgb, cv2.COLOR_RGB2BGR)
            smooth_mask = cv2.resize(patch_color_bgr, (w, h), interpolation=cv2.INTER_CUBIC)
        else:
            smooth_mask = np.zeros((h, w, 3), dtype=np.uint8)

        # 1. Build Base Visual Layout
        if mode == self.VIEW_DUAL:
            left_pane = frame_bgr.copy()
            if is_calibrating:
                right_pane = frame_bgr.copy()
                curr_frame, max_calib = calibration_progress
                cv2.putText(
                    right_pane,
                    f"CALIBRATING RETINAL MATRIX: {curr_frame}/{max_calib}",
                    (20, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 165, 255),
                    2,
                    cv2.LINE_AA,
                )
            else:
                right_pane = cv2.addWeighted(frame_bgr, 0.25, smooth_mask, 0.75, 0)
                cv2.putText(
                    right_pane,
                    "DINO FEATURE SEGMENTATION",
                    (10, 18),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.40,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
            display_window = np.hstack((left_pane, right_pane))

        elif mode == self.VIEW_BLENDED:
            if is_calibrating:
                display_window = frame_bgr.copy()
            else:
                display_window = cv2.addWeighted(
                    frame_bgr,
                    self.camera_weight,
                    smooth_mask,
                    self.heatmap_weight,
                    0,
                )
        elif mode == self.VIEW_HEATMAP_ONLY:
            display_window = smooth_mask.copy() if not is_calibrating else frame_bgr.copy()
        else:
            display_window = frame_bgr.copy()

        disp_h, disp_w, _ = display_window.shape

        # 2. Top Header Display Strip
        cv2.rectangle(display_window, (0, 0), (disp_w, 26), (15, 15, 15), -1)
        mode_label = self.VIEW_MODE_NAMES[mode]
        header_text = (
            f"Cozmo Vision Core ── Model: {model_name.upper()} | Frame: {frame_count} | "
            f"Mode: {mode_label} | Latency: {latency_ms:.0f}ms"
        )
        cv2.putText(
            display_window,
            header_text,
            (10, 17),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (0, 255, 200),
            1,
            cv2.LINE_AA,
        )

        # 3. Bottom REMIND Analytics Strip
        if is_calibrating:
            bar_color = (0, 165, 255)
            class_str = f"CALIBRATING ({calibration_progress[0]}/{calibration_progress[1]})"
            bar_width = int(220 * (calibration_progress[0] / max(1, calibration_progress[1])))
        else:
            if novelty_score > 0.60:
                bar_color = (0, 0, 255)       # Red: Novel Object
            elif novelty_score > 0.35:
                bar_color = (0, 255, 255)     # Yellow: Partially Familiar
            else:
                bar_color = (0, 255, 0)       # Green: Familiar Anchor
            class_str = classification
            bar_width = int(220 * min(max(novelty_score, 0.0), 1.0))

        bar_max_w = min(220, disp_w - 40)
        cv2.rectangle(display_window, (15, disp_h - 40), (15 + bar_max_w, disp_h - 30), (45, 45, 45), -1)
        cv2.rectangle(display_window, (15, disp_h - 40), (15 + bar_width, disp_h - 30), bar_color, -1)

        status_text = (
            f"Novelty: {novelty_score:.2f} ({class_str}) | Bank: {active_memories}/{max_memories} | "
            f"Discovered: {total_objects}"
        )
        cv2.putText(
            display_window,
            status_text,
            (15, disp_h - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            bar_color,
            1,
            cv2.LINE_AA,
        )

        # 4. Critical Hardware Safety Alert Banner
        if alert_text:
            cv2.rectangle(display_window, (0, 30), (disp_w, 62), (0, 0, 230), -1)
            cv2.putText(
                display_window,
                f"⚠️  {alert_text}",
                (20, 52),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        # 5. Draw Detected Object Bounding Boxes
        if detections:
            display_window = self.draw_detected_objects(display_window, detections, is_dual=(mode == self.VIEW_DUAL))

        # 6. Draw User Mouse Click/Drag Selection Highlight
        if selection_bbox:
            display_window = self.draw_selection_highlight(
                display_window,
                bbox_norm=selection_bbox,
                mask=selection_mask,
                is_dual=(mode == self.VIEW_DUAL),
            )

        # 7. Draw Center Focus Target Reticle if requested (and no manual mouse selection active)
        if show_reticle and not selection_bbox:
            display_window = self.draw_focus_reticle(display_window, reticle_box=reticle_box, is_dual=(mode == self.VIEW_DUAL))

        return display_window

    def draw_selection_highlight(
        self,
        frame_bgr: np.ndarray,
        bbox_norm: Tuple[float, float, float, float],
        mask: Optional[np.ndarray] = None,
        label: str = "CLICKED OBJECT [Press 'T' to Name | Right-Click to Clear]",
        is_dual: bool = False,
    ) -> np.ndarray:
        """Draws glowing magenta/cyan highlight and bounding box over the user-selected object."""
        h, full_w, _ = frame_bgr.shape
        w = full_w // 2 if is_dual else full_w

        ymin, xmin, ymax, xmax = bbox_norm
        x1, y1 = int(xmin * w), int(ymin * h)
        x2, y2 = int(xmax * w), int(ymax * h)

        color = (255, 0, 255)  # Magenta selection glow

        # If mask is provided, blend colored overlay on object pixels
        if mask is not None:
            mask_resized = cv2.resize(mask.astype(np.uint8) * 255, (w, h), interpolation=cv2.INTER_NEAREST)
            if is_dual:
                overlay = frame_bgr[:, :w].copy()
                overlay[mask_resized > 0] = (
                    0.5 * overlay[mask_resized > 0] + 0.5 * np.array([255, 0, 200])
                ).astype(np.uint8)
                frame_bgr[:, :w] = overlay
            else:
                overlay = frame_bgr.copy()
                overlay[mask_resized > 0] = (
                    0.5 * overlay[mask_resized > 0] + 0.5 * np.array([255, 0, 200])
                ).astype(np.uint8)
                frame_bgr[:] = overlay

        # Draw glowing dashed bounding box
        cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, 2)

        # Header tag
        tag_w = len(label) * 8 + 16
        cv2.rectangle(frame_bgr, (x1, max(30, y1 - 22)), (x1 + tag_w, max(30, y1 - 2)), color, -1)
        cv2.putText(
            frame_bgr,
            label,
            (x1 + 6, max(44, y1 - 7)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.36,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        return frame_bgr

    def draw_focus_reticle(
        self,
        frame_bgr: np.ndarray,
        reticle_box: Tuple[float, float, float, float] = (0.25, 0.25, 0.75, 0.75),
        label: str = "TARGET RETICLE [Press 'T' to Teach]",
        is_dual: bool = False,
    ) -> np.ndarray:
        """Draws a modern glowing sci-fi focus reticle box [ + ] over the camera frame."""
        h, full_w, _ = frame_bgr.shape
        w = full_w // 2 if is_dual else full_w

        ymin, xmin, ymax, xmax = reticle_box
        x1, y1 = int(xmin * w), int(ymin * h)
        x2, y2 = int(xmax * w), int(ymax * h)
        box_w = x2 - x1
        box_h = y2 - y1
        line_len = min(25, int(min(box_w, box_h) * 0.25))

        color = (0, 255, 255)  # Cyan-Yellow focus glow
        thickness = 2

        # Draw Corner Brackets
        # Top-Left
        cv2.line(frame_bgr, (x1, y1), (x1 + line_len, y1), color, thickness)
        cv2.line(frame_bgr, (x1, y1), (x1, y1 + line_len), color, thickness)
        # Top-Right
        cv2.line(frame_bgr, (x2, y1), (x2 - line_len, y1), color, thickness)
        cv2.line(frame_bgr, (x2, y1), (x2, y1 + line_len), color, thickness)
        # Bottom-Left
        cv2.line(frame_bgr, (x1, y2), (x1 + line_len, y2), color, thickness)
        cv2.line(frame_bgr, (x1, y2), (x1, y2 - line_len), color, thickness)
        # Bottom-Right
        cv2.line(frame_bgr, (x2, y2), (x2 - line_len, y2), color, thickness)
        cv2.line(frame_bgr, (x2, y2), (x2, y2 - line_len), color, thickness)

        # Center Crosshair
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.line(frame_bgr, (cx - 10, cy), (cx + 10, cy), color, 1)
        cv2.line(frame_bgr, (cx, cy - 10), (cx, cy + 10), color, 1)
        cv2.circle(frame_bgr, (cx, cy), 3, color, -1)

        # Reticle Top Label Tag
        cv2.rectangle(frame_bgr, (x1, max(30, y1 - 22)), (x1 + len(label) * 8 + 14, max(30, y1 - 2)), (20, 20, 20), -1)
        cv2.putText(
            frame_bgr,
            label,
            (x1 + 6, max(44, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.36,
            color,
            1,
            cv2.LINE_AA,
        )

        return frame_bgr

    def draw_detected_objects(
        self,
        frame_bgr: np.ndarray,
        detections: List[Dict[str, Any]],
        is_dual: bool = False,
    ) -> np.ndarray:
        """Draws bounding boxes and labels for all recognized visual anchors."""
        h, full_w, _ = frame_bgr.shape
        w = full_w // 2 if is_dual else full_w

        for det in detections:
            ymin, xmin, ymax, xmax = det.get("bbox_norm", (0, 0, 0, 0))
            label = det.get("label", "ANCHOR")
            conf = det.get("confidence", 0.0)

            x1, y1 = int(xmin * w), int(ymin * h)
            x2, y2 = int(xmax * w), int(ymax * h)

            # Draw sleek green bounding box
            color = (0, 230, 0)
            cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), color, 2)

            # Badge Header
            badge_str = f"{label.upper()} ({conf*100:.1f}%)"
            badge_w = len(badge_str) * 8 + 16
            cv2.rectangle(frame_bgr, (x1, max(30, y1 - 22)), (x1 + badge_w, max(30, y1 - 2)), color, -1)
            cv2.putText(
                frame_bgr,
                badge_str,
                (x1 + 6, max(44, y1 - 7)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        return frame_bgr


def render_cozmo_frame_heatmap(
    raw_frame: Union[np.ndarray, Image.Image],
    extractor: DINOPrecisionExtractor,
    visualizer: Optional[DINOHeatmapVisualizer] = None,
    remind_engine: Optional[Any] = None,
    robot_pose: Optional[Tuple[float, float, float]] = None,
    is_calibrating: bool = False,
    is_cozmo_cam: bool = True,
    view_mode: Optional[int] = None,
    frame_count: int = 1,
    alert_text: Optional[str] = None,
    show_reticle: bool = False,
    reticle_box: Tuple[float, float, float, float] = (0.25, 0.25, 0.75, 0.75),
    detections: Optional[List[Dict[str, Any]]] = None,
    selection_bbox: Optional[Tuple[float, float, float, float]] = None,
    selection_mask: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:


    """
    End-to-End One-Call Cozmo Vision Pipeline:
    1. Enhances Cozmo camera exposure & color balance.
    2. Runs high-precision DINO feature & spatial heatmap extraction.
    3. Evaluates REMIND novelty memory index if engine is provided.
    4. Generates modern composite HUD image ready for streaming or display.

    Returns:
        composite_bgr: Final UI rendered frame ready for cv2.imshow / WebRTC / RTSP stream.
        patch_color_rgb: Low-res patch color grid (RGB uint8).
        telemetry: Dictionary containing latency, novelty, classification, and memory counts.
    """
    # Convert input to BGR numpy
    if isinstance(raw_frame, Image.Image):
        rgb_np = np.array(raw_frame.convert("RGB"))
        frame_bgr = cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR)
    else:
        frame_bgr = raw_frame.copy()

    # 1. Hardware Sensor Enhancement
    if is_cozmo_cam:
        calibrated_bgr = enhance_cozmo_frame(frame_bgr)
    else:
        calibrated_bgr = frame_bgr

    # 2. Extract DINO Features
    t0 = time.time()
    pil_for_dino = Image.fromarray(cv2.cvtColor(calibrated_bgr, cv2.COLOR_BGR2RGB))
    global_feat, patch_color_rgb = extractor.extract(pil_for_dino, is_calibrating=is_calibrating)
    latency_ms = (time.time() - t0) * 1000.0

    # 3. Process REMIND Memory Bank
    novelty = 1.0 if is_calibrating else 0.0
    classification = "CALIBRATING RETINAL MATRIX" if is_calibrating else "INITIALIZING..."
    active_mems = 0
    total_objs = 0

    if remind_engine is not None and not is_calibrating:
        if hasattr(remind_engine, "process_feature"):
            try:
                if robot_pose is not None:
                    rx, ry, rtheta = robot_pose
                    res = remind_engine.process_feature(global_feat, rx, ry, rtheta)
                else:
                    res = remind_engine.process_feature(global_feat)
            except TypeError:
                res = remind_engine.process_feature(global_feat)

            if isinstance(res, tuple):
                novelty = float(res[0])
                if len(res) > 1 and isinstance(res[1], str):
                    classification = res[1]
                else:
                    classification = "NOVEL" if novelty > 0.6 else ("FAMILIAR" if novelty < 0.35 else "PARTIAL")


        if hasattr(remind_engine, "memory_bank"):
            bank = remind_engine.memory_bank
            active_mems = len(bank)
            total_objs = getattr(remind_engine, "total_objects_found", active_mems)

    # 4. Render Composite Frame
    viz = visualizer or DINOHeatmapVisualizer()
    composite_bgr = viz.render_composite(
        frame_bgr=calibrated_bgr,
        patch_color_rgb=patch_color_rgb,
        is_calibrating=is_calibrating,
        calibration_progress=(frame_count, extractor.calibration_target),
        novelty_score=novelty,
        classification=classification,
        active_memories=active_mems,
        max_memories=getattr(remind_engine, "max_capacity", 500) if remind_engine else 500,
        total_objects=total_objs,
        latency_ms=latency_ms,
        model_name=extractor.backend,
        frame_count=frame_count,
        alert_text=alert_text,
        view_mode=view_mode,
        show_reticle=show_reticle,
        reticle_box=reticle_box,
        detections=detections,
        selection_bbox=selection_bbox,
        selection_mask=selection_mask,
    )



    telemetry = {
        "latency_ms": latency_ms,
        "novelty": novelty,
        "classification": classification,
        "active_memories": active_mems,
        "total_objects": total_objs,
        "model": extractor.backend,
        "is_calibrating": is_calibrating,
    }

    return composite_bgr, patch_color_rgb, telemetry


# Global Shared Singleton Instances for Vision Subsystem
dino_heatmap_extractor = DINOPrecisionExtractor(lazy_init=True)
dino_heatmap_visualizer = DINOHeatmapVisualizer()
