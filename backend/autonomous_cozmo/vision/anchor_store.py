"""
Moka AI Assistant - Autonomous Cozmo Vision Subsystem
Persistent Visual Anchor & Semantic Object Store (visual_anchors.json).

Provides:
1. VisualAnchor: Dataclass representing a persistently grounded visual landmark or object.
2. VisualAnchorStore: Thread-safe persistent JSON database that serializes DINO 384-D semantic embeddings,
   desk coordinates, timestamps, and confidence metrics to disk. Supports real-time cosine similarity
   re-identification and pose updating.
"""

import os
import json
import time
import uuid
import math
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np


# Terminal formatting colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


@dataclass
class VisualAnchor:
    """Represents a permanently stored visual landmark or named desk object."""
    label: str
    feature_vector: List[float]
    estimated_x: float = 0.0
    estimated_y: float = 0.0
    estimated_theta_deg: float = 0.0
    confidence_threshold: float = 0.72
    is_permanent: bool = True
    created_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)
    observation_count: int = 1
    notes: str = ""

    def get_numpy_vector(self) -> np.ndarray:
        """Returns the feature vector as an L2-normalized float32 numpy array."""
        vec = np.array(self.feature_vector, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec /= norm
        return vec


@dataclass
class TransientObstacle:
    """Represents an unnamed floor obstacle or physical clutter."""
    id: str
    x: float
    y: float
    radius: float = 25.0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    confidence: float = 0.80
    observation_count: int = 1


def estimate_ground_position(
    bbox_norm: Tuple[float, float, float, float],
    robot_pose: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    head_angle_rad: float = 0.26,  # ~15 degrees
    cam_height_mm: float = 45.0,
    fov_v_deg: float = 47.0,
    fov_h_deg: float = 60.0,
) -> Tuple[float, float, float]:
    """
    Inverse Perspective Ground Contact Raycasting (Pinhole Model on Floor Plane z=0):
    Calculates the 2D world coordinates (X_world, Y_world, distance_mm) of an object
    based on the bottom edge of its bounding box touching the floor.
    """
    ymin, xmin, ymax, xmax = bbox_norm
    rx, ry, r_theta_deg = robot_pose
    r_theta_rad = math.radians(r_theta_deg)

    # 1. Vertical ground ray angle
    fov_v_rad = math.radians(fov_v_deg)
    y_bottom = float(ymax)  # Ground contact point
    phi_elev = -(y_bottom - 0.5) * fov_v_rad
    total_angle = -(head_angle_rad + phi_elev)

    # Prevent division by zero if looking above horizontal
    if total_angle < math.radians(2.0):
        total_angle = math.radians(2.0)

    # 2. Forward ground distance
    d_forward = cam_height_mm / math.tan(total_angle)
    d_forward = max(35.0, min(1200.0, d_forward))

    # 3. Horizontal azimuth angle and lateral offset
    fov_h_rad = math.radians(fov_h_deg)
    x_center = (xmin + xmax) / 2.0
    phi_azimuth = (x_center - 0.5) * fov_h_rad
    d_lateral = d_forward * math.tan(phi_azimuth)

    # 4. Transform to global world coordinates using robot heading
    cos_t = math.cos(r_theta_rad)
    sin_t = math.sin(r_theta_rad)

    world_x = rx + (cos_t * d_forward - sin_t * d_lateral)
    world_y = ry + (sin_t * d_forward + cos_t * d_lateral)
    dist_total = math.hypot(d_forward, d_lateral)

    return float(world_x), float(world_y), float(dist_total)



class VisualAnchorStore:
    """
    Thread-safe persistent JSON store for Cozmo's semantic visual memory.
    Saves and loads labeled visual embeddings from disk (backend/data/visual_anchors.json).
    """

    DEFAULT_STORE_PATH = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../backend/data/visual_anchors.json")
    )

    def __init__(self, store_path: Optional[str] = None):
        self.store_path = os.path.abspath(store_path or self.DEFAULT_STORE_PATH)
        self._lock = threading.RLock()
        self._anchors: Dict[str, VisualAnchor] = {}
        self._ensure_storage_dir()
        self.load_anchors()

    def _ensure_storage_dir(self):
        """Creates parent directories if they don't exist."""
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)

    def load_anchors(self) -> Dict[str, VisualAnchor]:
        """Loads stored visual anchors from the JSON file."""
        with self._lock:
            if not os.path.exists(self.store_path):
                self._anchors = {}
                return self._anchors

            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                self._anchors = {}
                for key, item in raw_data.items():
                    self._anchors[key] = VisualAnchor(
                        label=item.get("label", key),
                        feature_vector=item.get("feature_vector", []),
                        estimated_x=float(item.get("estimated_x", 0.0)),
                        estimated_y=float(item.get("estimated_y", 0.0)),
                        estimated_theta_deg=float(item.get("estimated_theta_deg", 0.0)),
                        confidence_threshold=float(item.get("confidence_threshold", 0.72)),
                        is_permanent=bool(item.get("is_permanent", True)),
                        created_at=float(item.get("created_at", time.time())),
                        last_seen_at=float(item.get("last_seen_at", time.time())),
                        observation_count=int(item.get("observation_count", 1)),
                        notes=str(item.get("notes", "")),
                    )
                return self._anchors
            except Exception as e:
                print(f"{YELLOW}[VisualAnchorStore] Warning loading {self.store_path}: {e}. Starting fresh.{RESET}")
                self._anchors = {}
                return self._anchors

    def save_to_disk(self):
        """Atomically saves in-memory anchors to the JSON file with Windows file-lock retry."""
        with self._lock:
            self._ensure_storage_dir()
            data_dict = {}
            for key, anchor in self._anchors.items():
                data_dict[key] = asdict(anchor)

            temp_path = f"{self.store_path}.{uuid.uuid4().hex[:8]}.tmp"
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data_dict, f, indent=2)
                
                # Retry loop for Windows file lock tolerance
                for attempt in range(4):
                    try:
                        if os.path.exists(self.store_path):
                            os.replace(temp_path, self.store_path)
                        else:
                            os.rename(temp_path, self.store_path)
                        self._last_disk_save_time = time.time()
                        break
                    except (PermissionError, OSError) as e:
                        if attempt == 3:
                            # Fallback: direct write
                            try:
                                with open(self.store_path, "w", encoding="utf-8") as f:
                                    json.dump(data_dict, f, indent=2)
                                self._last_disk_save_time = time.time()
                            except Exception as direct_err:
                                print(f"{YELLOW}[VisualAnchorStore] Disk write fallback failed: {direct_err}{RESET}")
                        else:
                            time.sleep(0.04 * (attempt + 1))
            except Exception as outer_err:
                print(f"{YELLOW}[VisualAnchorStore] Warning saving anchors: {outer_err}{RESET}")
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass


    def save_anchor(
        self,
        label: str,
        feature_vector: Union[np.ndarray, List[float]],
        x: float = 0.0,
        y: float = 0.0,
        theta_deg: float = 0.0,
        confidence_threshold: float = 0.72,
        is_permanent: bool = True,
        notes: str = "",
    ) -> VisualAnchor:
        """
        Stores or updates a labeled visual anchor in memory and persists to disk.
        """
        clean_label = label.strip()
        if isinstance(feature_vector, np.ndarray):
            norm = np.linalg.norm(feature_vector)
            if norm > 1e-6:
                vec = (feature_vector / norm).tolist()
            else:
                vec = feature_vector.tolist()
        else:
            vec = list(feature_vector)

        with self._lock:
            existing = self._anchors.get(clean_label)
            now = time.time()
            if existing:
                existing.feature_vector = vec
                existing.estimated_x = float(x)
                existing.estimated_y = float(y)
                existing.estimated_theta_deg = float(theta_deg)
                existing.confidence_threshold = float(confidence_threshold)
                existing.last_seen_at = now
                existing.observation_count += 1
                existing.notes = notes or existing.notes
                anchor = existing
            else:
                anchor = VisualAnchor(
                    label=clean_label,
                    feature_vector=vec,
                    estimated_x=float(x),
                    estimated_y=float(y),
                    estimated_theta_deg=float(theta_deg),
                    confidence_threshold=float(confidence_threshold),
                    is_permanent=is_permanent,
                    created_at=now,
                    last_seen_at=now,
                    observation_count=1,
                    notes=notes,
                )
                self._anchors[clean_label] = anchor

            self.save_to_disk()
            return anchor

    def identify(
        self,
        feature_vector: np.ndarray,
        min_similarity: Optional[float] = None,
    ) -> Tuple[Optional[str], float, Optional[VisualAnchor]]:
        """
        Compares an observed feature vector against all stored anchors using Cosine Similarity.
        Returns: (matched_label, similarity_score, matched_anchor_obj) or (None, max_sim, None)
        """
        with self._lock:
            if not self._anchors:
                return None, 0.0, None

            feat_norm = feature_vector / (np.linalg.norm(feature_vector) + 1e-8)
            best_sim = -1.0
            best_anchor = None
            best_label = None

            for label, anchor in self._anchors.items():
                anchor_vec = anchor.get_numpy_vector()
                sim = float(np.dot(feat_norm, anchor_vec))
                threshold = min_similarity if min_similarity is not None else anchor.confidence_threshold

                if sim > best_sim:
                    best_sim = sim
                    if sim >= threshold:
                        best_label = label
                        best_anchor = anchor
                    else:
                        best_label = None
                        best_anchor = None

            if best_anchor is not None:
                # Update observation metadata
                best_anchor.last_seen_at = time.time()
                best_anchor.observation_count += 1
                return best_label, best_sim, best_anchor

            return None, max(0.0, best_sim), None

    def detect_objects_in_patches(
        self,
        patch_tokens_grid: np.ndarray,
        min_patch_similarity: float = 0.74,
        min_matching_patches: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Scans all spatial patches across the frame against stored visual anchors.
        Returns localized bounding boxes (normalized [ymin, xmin, ymax, xmax])
        for all recognized objects in the scene!
        """
        with self._lock:
            if not self._anchors or patch_tokens_grid is None:
                return []

            grid_h, grid_w, dim = patch_tokens_grid.shape
            detections = []

            for label, anchor in self._anchors.items():
                anchor_vec = anchor.get_numpy_vector()
                # Compute dot product across all grid patches (grid_h, grid_w)
                sim_map = np.dot(patch_tokens_grid, anchor_vec)
                threshold = max(min_patch_similarity, anchor.confidence_threshold)
                match_mask = (sim_map >= threshold)
                match_count = int(np.count_nonzero(match_mask))

                if match_count >= min_matching_patches:
                    coords = np.argwhere(match_mask)
                    r_min, c_min = coords.min(axis=0)
                    r_max, c_max = coords.max(axis=0) + 1

                    ymin = float(r_min / grid_h)
                    xmin = float(c_min / grid_w)
                    ymax = float(r_max / grid_h)
                    xmax = float(c_max / grid_w)

                    conf = float(np.mean(sim_map[match_mask]))
                    anchor.last_seen_at = time.time()
                    anchor.observation_count += 1

                    detections.append({
                        "label": label,
                        "confidence": conf,
                        "bbox_norm": (ymin, xmin, ymax, xmax),
                        "num_patches": match_count,
                        "anchor": anchor,
                    })

            return detections

    def update_anchor_pose(
        self,
        label: str,
        new_x: float,
        new_y: float,
        new_theta_deg: Optional[float] = None,
        force_save: bool = False,
    ) -> bool:
        """Updates stored desk coordinates for a recognized anchor with throttled disk persistence."""
        with self._lock:
            anchor = self._anchors.get(label)
            if anchor:
                old_x, old_y = anchor.estimated_x, anchor.estimated_y
                anchor.estimated_x = float(new_x)
                anchor.estimated_y = float(new_y)
                if new_theta_deg is not None:
                    anchor.estimated_theta_deg = float(new_theta_deg)
                anchor.last_seen_at = time.time()

                # Debounce disk writes (only write if moved > 25mm or > 5s elapsed)
                dist = math.hypot(anchor.estimated_x - old_x, anchor.estimated_y - old_y)
                last_save = getattr(self, "_last_disk_save_time", 0.0)
                if force_save or dist > 25.0 or (time.time() - last_save > 5.0):
                    self.save_to_disk()
                return True
            return False


    def update_or_relocate_anchor(
        self,
        label: str,
        observed_x: float,
        observed_y: float,
        confidence: float = 0.85,
        smoothing_alpha: float = 0.65,
    ) -> Optional[VisualAnchor]:
        """
        Dynamically updates the spatial position of an observed anchor.
        If the object was moved/relocated by > 35mm, smoothly updates coordinates
        and marks an updated timestamp without creating duplicate ghost landmarks!
        """
        with self._lock:
            anchor = self._anchors.get(label)
            if not anchor:
                return None

            old_x, old_y = anchor.estimated_x, anchor.estimated_y
            disp = math.hypot(observed_x - old_x, observed_y - old_y)

            # If anchor moved noticeably (> 35mm) with high confidence, relocate it
            if disp > 35.0 and confidence >= anchor.confidence_threshold:
                # Apply smoothing filter
                anchor.estimated_x = float(smoothing_alpha * observed_x + (1.0 - smoothing_alpha) * old_x)
                anchor.estimated_y = float(smoothing_alpha * observed_y + (1.0 - smoothing_alpha) * old_y)
                anchor.last_seen_at = time.time()
                anchor.observation_count += 1
                self.save_to_disk()
            else:
                # Minor drift update
                anchor.last_seen_at = time.time()
                anchor.observation_count += 1
                if disp > 5.0:
                    anchor.estimated_x = float(0.2 * observed_x + 0.8 * old_x)
                    anchor.estimated_y = float(0.2 * observed_y + 0.8 * old_y)

            return anchor

    def register_or_update_obstacle(
        self,
        obs_x: float,
        obs_y: float,
        confidence: float = 0.80,
        radius: float = 25.0,
    ) -> TransientObstacle:
        """Registers a newly discovered floor obstacle or updates an existing nearby obstacle."""
        with self._lock:
            if not hasattr(self, "_obstacles"):
                self._obstacles: Dict[str, TransientObstacle] = {}

            now = time.time()
            # Check if close to an existing obstacle (< 40mm)
            for obs_id, obs in self._obstacles.items():
                if math.hypot(obs.x - obs_x, obs.y - obs_y) < 40.0:
                    obs.x = 0.5 * obs.x + 0.5 * obs_x
                    obs.y = 0.5 * obs.y + 0.5 * obs_y
                    obs.last_seen = now
                    obs.observation_count += 1
                    obs.confidence = max(obs.confidence, confidence)
                    return obs

            # Create new obstacle
            new_id = f"obs_{len(self._obstacles) + 1}_{int(now) % 10000}"
            new_obs = TransientObstacle(
                id=new_id,
                x=float(obs_x),
                y=float(obs_y),
                radius=float(radius),
                first_seen=now,
                last_seen=now,
                confidence=float(confidence),
                observation_count=1,
            )
            self._obstacles[new_id] = new_obs
            return new_obs

    def list_obstacles(self) -> List[TransientObstacle]:
        """Returns all currently tracked ground obstacles."""
        with self._lock:
            if not hasattr(self, "_obstacles"):
                self._obstacles = {}
            return list(self._obstacles.values())

    def prune_stale_obstacles(self, max_age_s: float = 60.0) -> int:
        """Removes transient obstacles that haven't been seen recently."""
        with self._lock:
            if not hasattr(self, "_obstacles"):
                self._obstacles = {}
                return 0
            now = time.time()
            to_del = [k for k, v in self._obstacles.items() if now - v.last_seen > max_age_s]
            for k in to_del:
                del self._obstacles[k]
            return len(to_del)

    def get_anchor(self, label: str) -> Optional[VisualAnchor]:
        """Returns the anchor object for a given label."""
        with self._lock:
            return self._anchors.get(label)

    def delete_anchor(self, label: str) -> bool:
        """Deletes an anchor from storage."""
        with self._lock:
            if label in self._anchors:
                del self._anchors[label]
                self.save_to_disk()
                return True
            return False

    def list_anchors(self) -> List[VisualAnchor]:
        """Returns a list of all currently stored visual anchors."""
        with self._lock:
            return list(self._anchors.values())

    def clear(self):
        """Clears all stored anchors and obstacles."""
        with self._lock:
            self._anchors.clear()
            if hasattr(self, "_obstacles"):
                self._obstacles.clear()
            self.save_to_disk()


# Global Singleton Visual Anchor Store
visual_anchor_store = VisualAnchorStore()

