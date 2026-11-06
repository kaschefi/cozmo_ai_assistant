# backend/test/routers/models/__init__.py
"""
Aggregated router models package organizing all 6 benchmark architectures:

LLM Models:
- baseline_router_predictor (Monolithic Qwen2.5:3b / WP2)
- get_baseline_router_predictor (Scaled N-tools baseline LLM)
- two_layer_llm_predictor (FastEmbed Reflexes + Tool RAG + LLM / WP2)
- get_two_layer_llm_predictor (Scaled N-tools Two-Layer LLM)

LAYA Models:
- single_layer_laya_predictor (Monolithic LAYA cross-encoder / WP2)
- get_single_layer_laya_predictor (Scaled N-tools single-layer LAYA)
- two_layer_laya_predictor (FastEmbed Reflexes + Monolithic LAYA / WP2)
- get_two_layer_laya_predictor (Scaled N-tools two-layer LAYA)
- single_layer_laya_topk_predictor (Tool RAG + LAYA Top-K / WP2)
- get_single_layer_laya_topk_predictor (Scaled N-tools Top-K LAYA)
- two_layer_laya_topk_predictor (FastEmbed Reflexes + Tool RAG + LAYA Top-K / WP2)
- get_two_layer_laya_topk_predictor (Scaled N-tools two-layer Top-K LAYA)
"""

from test.routers.models.llm import (
    baseline_router_predictor,
    get_baseline_router_predictor,
    test_baseline_router_wp2,
    two_layer_llm_predictor,
    get_two_layer_llm_predictor,
    test_two_layer_llm_router_wp2,
)
from test.routers.models.laya import (
    single_layer_laya_predictor,
    get_single_layer_laya_predictor,
    test_single_layer_laya_router_wp2,
    single_layer_laya_topk_predictor,
    get_single_layer_laya_topk_predictor,
    test_single_layer_laya_topk_router_wp2,
    two_layer_laya_predictor,
    get_two_layer_laya_predictor,
    test_two_layer_laya_router_wp2,
    two_layer_laya_topk_predictor,
    get_two_layer_laya_topk_predictor,
    test_two_layer_laya_topk_router_wp2,
)

__all__ = [
    # LLM
    "baseline_router_predictor",
    "get_baseline_router_predictor",
    "test_baseline_router_wp2",
    "two_layer_llm_predictor",
    "get_two_layer_llm_predictor",
    "test_two_layer_llm_router_wp2",
    # LAYA
    "single_layer_laya_predictor",
    "get_single_layer_laya_predictor",
    "test_single_layer_laya_router_wp2",
    "single_layer_laya_topk_predictor",
    "get_single_layer_laya_topk_predictor",
    "test_single_layer_laya_topk_router_wp2",
    "two_layer_laya_predictor",
    "get_two_layer_laya_predictor",
    "test_two_layer_laya_router_wp2",
    "two_layer_laya_topk_predictor",
    "get_two_layer_laya_topk_predictor",
    "test_two_layer_laya_topk_router_wp2",
]
