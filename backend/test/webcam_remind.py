import sys
import time
import numpy as np
import cv25
from PIL import Image
import torch
import torchvision.transforms as T

# Terminal interface styling profile
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
GRAY = "\033[90m"
RESET = "\033[0m"


# -----------------------------------------------------------------------------
# PRODUCTION-GRADE STABILIZED DINO EXTRACTOR
# -----------------------------------------------------------------------------

class ProductionDINOExtractor:
    """
    Advanced DINOv2 Feature Extractor featuring an initialization calibration phase.
    Locks eigenvectors globally to eliminate all sign flips and semantic color drift.
    """

    def __init__(self, model_name: str = "dinov2_vits14", calibration_frames: int = 30):
        print(f"{BLUE}[DINO Init] Loading foundation model weights ({model_name})...{RESET}")
        self.device = torch.device("cpu")
        try:
            self.model = torch.hub.load("facebookresearch/dinov2", model_name)
            self.model.eval().to(self.device)
            print(f"{GREEN}[DINO Init] Backbone safely loaded into RAM!{RESET}")
        except Exception as e:
            print(f"{RED}[CRITICAL ERROR] Failed to load hub asset: {e}{RESET}")
            raise e

        self.transform = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        # Calibration state metrics
        self.calibration_target = calibration_frames
        self.calibration_pool = []
        self.master_eigenvectors = None
        self.global_min = None
        self.global_max = None

        # Temporal smoothing window parameter
        self.prev_mask = None
        self.alpha = 0.30  # Moving average smoothing coefficient

    def extract(self, pil_image: Image.Image, is_calibrating: bool = True):
        tensor = self.transform(pil_image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            patch_tokens = self.model.get_intermediate_layers(tensor, n=1)[0].squeeze(0)  # (256, 384)
            patch_tokens_norm = torch.nn.functional.normalize(patch_tokens, p=2, dim=1)

            # Global image descriptor for REMIND novelty checks
            global_feat = patch_tokens_norm.mean(dim=0, keepdim=True)
            global_feat_norm = torch.nn.functional.normalize(global_feat, p=2, dim=1).squeeze(0).cpu().numpy()

            # --- PHASE 1: CALIBRATION PROCESS ---
            if is_calibrating:
                self.calibration_pool.append(patch_tokens_norm.cpu().numpy())
                return global_feat_norm, np.zeros((16, 16, 3), dtype=np.uint8)

            # --- PHASE 2: COMPILE MASTER COGNITIVE SPACE ---
            if self.master_eigenvectors is None:
                print(f"\n{MAGENTA}[CALIBRATION COMPLETE] Fitting Master Space over accumulated tensors...{RESET}")
                combined_pool = np.vstack(self.calibration_pool)
                mean_centered = combined_pool - np.mean(combined_pool, axis=0)
                _, _, Vh = np.linalg.svd(mean_centered, full_matrices=False)

                self.master_eigenvectors = Vh[:3, :].T  # Dimensions: (384, 3)

                for i in range(3):
                    max_abs_idx = np.argmax(np.abs(self.master_eigenvectors[:, i]))
                    if self.master_eigenvectors[max_abs_idx, i] < 0:
                        self.master_eigenvectors[:, i] = -self.master_eigenvectors[:, i]

                projected_pool = np.dot(combined_pool, self.master_eigenvectors)
                self.global_min = projected_pool.min(axis=0)
                self.global_max = projected_pool.max(axis=0)
                print(
                    f"{GREEN}[SYSTEM LOCK] Master PCA bounds locked down securely. Latent space drift eliminated.{RESET}")

            # --- PHASE 3: RUN DEPLOYMENT INFERENCE SPACE ---
            current_tokens = patch_tokens_norm.cpu().numpy()
            pca_3d = np.dot(current_tokens, self.master_eigenvectors)  # (256, 3)

            denom = np.where((self.global_max - self.global_min) == 0, 1.0, (self.global_max - self.global_min))
            norm_rgb = np.clip(((pca_3d - self.global_min) / denom) * 255.0, 0, 255).astype(np.uint8)
            patch_color_grid = norm_rgb.reshape((16, 16, 3))

            if self.prev_mask is not None:
                patch_color_grid = (self.alpha * patch_color_grid + (1.0 - self.alpha) * self.prev_mask).astype(
                    np.uint8)
            self.prev_mask = patch_color_grid

        return global_feat_norm, patch_color_grid


# -----------------------------------------------------------------------------
# REMIND REPLAY MEMORY INDEXING ENGINE
# -----------------------------------------------------------------------------

class REMINDMemoryEngine:
    def __init__(self, novelty_threshold: float = 0.35, max_capacity: int = 500):
        self.novelty_threshold = novelty_threshold
        self.max_capacity = max_capacity
        self.memory_bank = []
        self.total_objects_found = 0  # Restored storage tracking metric

    def process_feature(self, feature_vector: np.ndarray):
        if len(self.memory_bank) == 0:
            self.memory_bank.append(feature_vector)
            self.total_objects_found += 1
            return 1.0, "ESTABLISHING VISUAL ANCHORS", 0.0, True

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
            classification = "NEW NOVEL ENVIRONMENT"
        elif novelty_score > 0.35:
            classification = "PARTIALLY FAMILIAR ANCHOR"
        else:
            classification = "RECOGNIZED OFFICE OBJECT"

        return novelty_score, classification, max_sim, stored_new

    def clear_memory(self):
        self.memory_bank.clear()
        # Reset tracker on purge if preferred, or leave rolling
        self.total_objects_found = 0


# -----------------------------------------------------------------------------
# MAIN APP FLOW RUNNER
# -----------------------------------------------------------------------------

def run_stabilized_webcam_pipeline():
    extractor = ProductionDINOExtractor(calibration_frames=30)
    remind_engine = REMINDMemoryEngine()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print(f"{RED}[ERROR] Webcam completely unavailable.{RESET}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    view_mode = 0
    view_modes = ["DUAL-VIEW INTERFACE", "BLENDED OVERLAY", "CLEAN BACKEND FEED"]
    frame_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            h, w, _ = frame.shape

            is_calibrating = frame_count <= extractor.calibration_target

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)

            t0 = time.time()
            global_feat, patch_color_rgb = extractor.extract(pil_img, is_calibrating=is_calibrating)

            if not is_calibrating:
                novelty, classification, max_sim, stored_new = remind_engine.process_feature(global_feat)
                latency_ms = (time.time() - t0) * 1000.0
                patch_color_bgr = cv2.cvtColor(patch_color_rgb, cv2.COLOR_RGB2BGR)
                smooth_mask = cv2.resize(patch_color_bgr, (w, h), interpolation=cv2.INTER_LINEAR)

                # Terminal alert flash when a brand new memory state is committed
                if stored_new:
                    print(
                        f"\n{GREEN}[REMIND NEW STORAGE] Committed unique object memory state! Total Stored: {remind_engine.total_objects_found}{RESET}")
            else:
                novelty, classification, latency_ms, stored_new = 1.0, "CALIBRATING RETINAL MATRIX...", 0.0, False
                smooth_mask = np.zeros((h, w, 3), dtype=np.uint8)

            # Interface layout compilation mappings
            if view_mode == 0:
                left_pane = frame.copy()
                right_pane = cv2.addWeighted(frame, 0.25, smooth_mask, 0.75, 0) if not is_calibrating else frame.copy()
                if is_calibrating:
                    cv2.putText(right_pane, f"CALIBRATING BASELINE SPACE: {frame_count}/{extractor.calibration_target}",
                                (20, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2, cv2.LINE_AA)
                display_window = np.hstack((left_pane, right_pane))
            elif view_mode == 1:
                display_window = cv2.addWeighted(frame, 0.50, smooth_mask, 0.50,
                                                 0) if not is_calibrating else frame.copy()
            else:
                display_window = frame.copy()

            disp_h, disp_w, _ = display_window.shape

            # Top Display Status Bar UI Strip
            cv2.rectangle(display_window, (0, 0), (disp_w, 25), (15, 15, 15), -1)
            cv2.putText(
                display_window,
                f"Moka Core ── Frame: {frame_count} | Mode: {view_modes[view_mode]} | Latency: {latency_ms:.0f}ms",
                (10, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 0), 1, cv2.LINE_AA
            )

            # Bottom Analytics Overlay Dashboard Panel UI
            bar_color = (0, 165, 255) if is_calibrating else (
                (0, 0, 255) if novelty > 0.60 else ((0, 255, 255) if novelty > 0.35 else (0, 255, 0)))
            bar_max_w = 200
            bar_width = int(bar_max_w * novelty)

            cv2.rectangle(display_window, (20, disp_h - 40), (20 + bar_max_w, disp_h - 32), (50, 50, 50), -1)
            cv2.rectangle(display_window, (20, disp_h - 40), (20 + bar_width, disp_h - 32), bar_color, -1)

            # Added Total Discoveries count to the on-screen display panel interface
            cv2.putText(
                display_window,
                f"Novelty: {novelty:.2f} ({classification}) | Active Bank: {len(remind_engine.memory_bank)}/500 | Total Stored: {remind_engine.total_objects_found}",
                (20, disp_h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.38, bar_color, 1, cv2.LINE_AA
            )

            cv2.imshow("Production-Grade Stabilized DINO Engine", display_window)

            # Handle system controls interaction loops
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("m"):
                view_mode = (view_mode + 1) % len(view_modes)
            elif key == ord("c"):
                remind_engine.clear_memory()

            # Enhanced live rolling logging layout inside terminal
            sys.stdout.write(
                f"\rStatus Matrix ──> State: {classification} | Novelty: {novelty:.2f} | "
                f"Memory Array: {len(remind_engine.memory_bank)} | Total Discoveries: {remind_engine.total_objects_found}"
            )
            sys.stdout.flush()

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(f"\n{GREEN}[COMPLETE] Pipeline cleanly closed down.{RESET}")


if __name__ == "__main__":
    run_stabilized_webcam_pipeline()