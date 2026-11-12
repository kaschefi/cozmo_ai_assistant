# core/routing/layer2/config.py
from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class Layer2Config:
    """Configuration and tuning thresholds for Layer 2 Cognitive Routing."""
    laya_model_id: str = "convaiinnovations/laya-typed-decisions"
    chat_model_id: str = "gemma4:e2b"
    chat_temperature: float = 0.6
    
    # Vector DB / Tool RAG Probe parameters
    probe_k: int = 8
    distance_threshold: float = 1.15
    weak_match_threshold: float = 1.10
    top_domain_score_threshold: float = 0.60
    domain_margin: float = 0.12
    tool_score_margin: float = 0.16
    max_candidate_tools: int = 4
    
    # Gating & Anti-hallucination thresholds
    none_override_max_conf: float = 0.12
    none_override_strong_match: float = 0.65
    none_override_min_prob: float = 0.25
    anti_hallucination_min_conf: float = 0.05
    anti_hallucination_weak_score: float = 0.82

    # Memory and summarization parameters
    default_user_id: str = "cozmo_owner"
    max_summary_trigger_length: int = 6
    summary_keep_recent_count: int = 4
    memory_retrieve_limit: int = 3
    meta_memory_limit: int = 15

    # Exclusions
    setup_exclusion_names: Tuple[str, ...] = ("setup_gaming", "setup_study", "setup_coding")


DEFAULT_CONFIG = Layer2Config()

