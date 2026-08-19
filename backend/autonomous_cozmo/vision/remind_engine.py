import time
import math
import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
from PIL import Image

from autonomous_cozmo.vision.dino_extractor import DINOExtractor

# Terminal formatting colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


@dataclass
class VisualMemoryItem:
    """Represents a discrete indexed object or environmental anchor in visual memory."""
    id: str
    name: str
    feature_vector: np.ndarray
    estimated_x: float
    estimated_y: float
    confidence: float = 1.0
    consecutive_hits: int = 1
    last_attended_time: float = 0.0
    observation_count: int = 1
    is_anchor: bool = False
    is_verified: bool = False  # Set to True once debounced over N frames
    attended_by_robot: bool = False


class TemporalDebouncer:
    """
    Filters out momentary lighting glints, camera sensor noise, and rapid target switching.
    Requires an observed visual cluster to persist across N consecutive frames before
    promoting it to verified status in the Behavior Tree target selector.
    """
    def __init__(self, required_consecutive_frames: int = 3, similarity_threshold: float = 0.75):
        self.required_frames = required_consecutive_frames
        self.similarity_threshold = similarity_threshold
        self._tentative_clusters: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def process_observation(self, feature_vector: np.ndarray, estimated_x: float, estimated_y: float) -> Tuple[bool, Optional[str]]:
        """
        Updates tentative cluster tracking.
        Returns: (is_confirmed, cluster_id)
        """
        with self._lock:
            best_match_id = None
            highest_sim = -1.0

            for c_id, data in list(self._tentative_clusters.items()):
                sim = float(np.dot(data["feature_vector"], feature_vector))
                if sim > highest_sim and sim >= self.similarity_threshold:
                    highest_sim = sim
                    best_match_id = c_id

            now = time.time()
            if best_match_id is not None:
                cluster = self._tentative_clusters[best_match_id]
                cluster["hits"] += 1
                cluster["last_seen"] = now
                cluster["x"] = 0.7 * cluster["x"] + 0.3 * estimated_x
                cluster["y"] = 0.7 * cluster["y"] + 0.3 * estimated_y
                # Running average feature
                cluster["feature_vector"] = 0.8 * cluster["feature_vector"] + 0.2 * feature_vector
                norm = np.linalg.norm(cluster["feature_vector"])
                if norm > 1e-6:
                    cluster["feature_vector"] /= norm

                is_confirmed = cluster["hits"] >= self.required_frames
                return is_confirmed, best_match_id
            else:
                # Create a new tentative cluster
                new_id = f"tentative_{uuid.uuid4().hex[:6]}"
                self._tentative_clusters[new_id] = {
                    "feature_vector": feature_vector.copy(),
                    "x": estimated_x,
                    "y": estimated_y,
                    "hits": 1,
                    "created_at": now,
                    "last_seen": now,
                }
                # Prune old unconfirmed clusters older than 4 seconds
                for c_id, data in list(self._tentative_clusters.items()):
                    if now - data["last_seen"] > 4.0:
                        del self._tentative_clusters[c_id]

                return False, new_id


class REMINDMemoryEngine:
    """
    Dynamic Visual Memory & Replay Indexer.
    Exposes an asynchronous query API for Behavior Trees and visual landmark tracking:
    - get_novel_objects()
    - get_least_recently_attended()
    - get_object_pose(id)
    - mark_attended(id)
    - register_anchor(name, x, y, feature_vector)
    """

    DEFAULT_NOVELTY_THRESHOLD = 0.35
    DEFAULT_MATCH_SIMILARITY = 0.72

    def __init__(
        self,
        novelty_threshold: float = DEFAULT_NOVELTY_THRESHOLD,
        match_similarity: float = DEFAULT_MATCH_SIMILARITY,
        required_consecutive_frames: int = 3,
        extractor: Optional[DINOExtractor] = None,
    ):
        self.novelty_threshold = novelty_threshold
        self.match_similarity = match_similarity
        self.extractor = extractor or DINOExtractor()
        self.debouncer = TemporalDebouncer(
            required_consecutive_frames=required_consecutive_frames,
            similarity_threshold=match_similarity,
        )

        self._lock = threading.RLock()
        self.memory_bank: Dict[str, VisualMemoryItem] = {}

        # Asynchronous frame worker queue
        self._frame_queue = queue.Queue(maxsize=2)
        self._worker_running = True
        self._worker_thread = threading.Thread(target=self._async_frame_worker, daemon=True)
        self._worker_thread.start()

    def process_frame_async(self, pil_image: Image.Image, robot_pose: Tuple[float, float, float]):
        """
        Enqueues a new camera frame for asynchronous background processing without blocking BT ticks.
        robot_pose: (eff_x, eff_y, eff_theta_deg)
        """
        try:
            # Skip frames if worker is busy
            if self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self._frame_queue.put_nowait((pil_image, robot_pose))
        except Exception:
            pass

    def _async_frame_worker(self):
        """Background thread extracting DINO features and updating visual memory."""
        while self._worker_running:
            try:
                item = self._frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            pil_img, (curr_x, curr_y, curr_theta_deg) = item
            try:
                feat = self.extractor.extract_features(pil_img)
                self.process_feature(feat, curr_x, curr_y, curr_theta_deg)
            except Exception as e:
                print(f"{YELLOW}[REMIND Worker Warning] {e}{RESET}")

    def process_feature(
        self,
        feature_vector: np.ndarray,
        curr_x: float,
        curr_y: float,
        curr_theta_deg: float,
        estimated_distance_mm: float = 120.0,
        explicit_target_x: Optional[float] = None,
        explicit_target_y: Optional[float] = None,
        custom_name: Optional[str] = None,
    ) -> Tuple[float, Optional[str], float]:
        """
        Processes an extracted feature vector:
        1. Estimates object desk coordinates (projected forward along heading or explicit).
        2. Applies temporal debouncer.
        3. Matches or registers in memory bank.
        Returns: (novelty_score, matched_or_created_item_id, max_sim)
        """
        if explicit_target_x is not None and explicit_target_y is not None:
            target_x = float(explicit_target_x)
            target_y = float(explicit_target_y)
        else:
            heading_rad = math.radians(curr_theta_deg)
            target_x = curr_x + estimated_distance_mm * math.cos(heading_rad)
            target_y = curr_y + estimated_distance_mm * math.sin(heading_rad)

        is_confirmed, debounced_id = self.debouncer.process_observation(feature_vector, target_x, target_y)

        with self._lock:
            if len(self.memory_bank) == 0:
                item_id = f"obj_{uuid.uuid4().hex[:6]}"
                name = custom_name or f"Desk Item #1"
                new_item = VisualMemoryItem(
                    id=item_id,
                    name=name,
                    feature_vector=feature_vector.copy(),
                    estimated_x=target_x,
                    estimated_y=target_y,
                    is_verified=is_confirmed,
                )
                self.memory_bank[item_id] = new_item
                return 1.0, item_id, 0.0

            # Match against existing memory bank
            best_id = None
            max_sim = -1.0
            for item_id, item in self.memory_bank.items():
                sim = float(np.dot(item.feature_vector, feature_vector))
                if sim > max_sim:
                    max_sim = sim
                    best_id = item_id

            novelty_score = float(np.clip(1.0 - max_sim, 0.0, 1.0))

            if max_sim >= self.match_similarity and best_id is not None:
                # Existing item recognized -> Update observations & smooth position
                matched_item = self.memory_bank[best_id]
                matched_item.observation_count += 1
                matched_item.estimated_x = 0.8 * matched_item.estimated_x + 0.2 * target_x
                matched_item.estimated_y = 0.8 * matched_item.estimated_y + 0.2 * target_y
                if is_confirmed:
                    matched_item.is_verified = True
                return novelty_score, best_id, max_sim
            else:
                # Novel object detected
                if novelty_score >= self.novelty_threshold:
                    item_id = f"obj_{uuid.uuid4().hex[:6]}"
                    name = custom_name or f"Desk Item #{len(self.memory_bank)+1}"
                    new_item = VisualMemoryItem(
                        id=item_id,
                        name=name,
                        feature_vector=feature_vector.copy(),
                        estimated_x=target_x,
                        estimated_y=target_y,
                        confidence=novelty_score,
                        is_verified=is_confirmed,
                    )
                    self.memory_bank[item_id] = new_item
                    return novelty_score, item_id, max_sim

            return novelty_score, best_id, max_sim

    def register_anchor(
        self,
        name: str,
        x: float,
        y: float,
        feature_vector: Optional[np.ndarray] = None,
    ) -> str:
        """Registers a fixed environmental anchor (e.g. Charging Dock, Monitor Stand)."""
        with self._lock:
            anchor_id = f"anchor_{name.lower().replace(' ', '_')}"
            if feature_vector is None:
                feature_vector = np.zeros(self.extractor.embedding_dim, dtype=np.float32)
                feature_vector[0] = 1.0

            item = VisualMemoryItem(
                id=anchor_id,
                name=name,
                feature_vector=feature_vector,
                estimated_x=float(x),
                estimated_y=float(y),
                is_anchor=True,
                is_verified=True,
                attended_by_robot=True,
            )
            self.memory_bank[anchor_id] = item
            return anchor_id

    def get_novel_objects(self, min_novelty_score: float = 0.35) -> List[VisualMemoryItem]:
        """
        Returns newly discovered objects that have not yet been attended to,
        filtered for debounced verified status.
        """
        with self._lock:
            novel = []
            for item in self.memory_bank.values():
                if not item.is_anchor and item.is_verified and not item.attended_by_robot:
                    novel.append(item)
            return novel

    def get_least_recently_attended(self) -> List[VisualMemoryItem]:
        """Returns all verified, previously attended objects sorted by oldest last_attended_time."""
        with self._lock:
            items = [item for item in self.memory_bank.values() if not item.is_anchor and item.is_verified and item.attended_by_robot]
            return sorted(items, key=lambda x: x.last_attended_time)

    def get_object_pose(self, object_id: str) -> Optional[Tuple[float, float]]:
        """Returns estimated (x, y) coordinates for a given object."""
        with self._lock:
            item = self.memory_bank.get(object_id)
            if item:
                return item.estimated_x, item.estimated_y
            return None

    def mark_attended(self, object_id: str):
        """Marks that Cozmo has arrived at and actively observed this object."""
        with self._lock:
            item = self.memory_bank.get(object_id)
            if item:
                item.attended_by_robot = True
                item.last_attended_time = time.time()
                item.observation_count += 1

    def update_object_pose(self, object_id: str, new_x: float, new_y: float):
        """Updates stored coordinates when an object is physically rearranged on the desk."""
        with self._lock:
            item = self.memory_bank.get(object_id)
            if item:
                item.estimated_x = float(new_x)
                item.estimated_y = float(new_y)

    def get_persistent_anchors(self) -> List[VisualMemoryItem]:
        """Returns all registered high-confidence environmental anchors."""
        with self._lock:
            return [item for item in self.memory_bank.values() if item.is_anchor]

    def clear(self):
        """Resets the visual memory bank."""
        with self._lock:
            self.memory_bank.clear()

    def shutdown(self):
        """Stops background worker thread."""
        self._worker_running = False


# Global singleton REMIND Memory Engine
remind_engine = REMINDMemoryEngine()
