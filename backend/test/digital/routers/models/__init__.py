# backend/test/digital/routers/models/__init__.py
"""
Aggregated router models package organizing the 6 WP2 benchmark architectures:

LLM Models:
- baseline_router_predictor (Monolithic Qwen2.5:3b)
- two_layer_llm_predictor (FastEmbed Reflexes + Tool RAG + Qwen2.5:3b)

LAYA Models:
- single_layer_laya_predictor (Monolithic LAYA cross-encoder)
- two_layer_laya_predictor (FastEmbed Reflexes + Monolithic LAYA)
- single_layer_laya_topk_predictor (Tool RAG + LAYA Top-K)
- two_layer_laya_topk_predictor (FastEmbed Reflexes + Tool RAG + LAYA Top-K)
"""

from test.digital.routers.models.llm import (
    baseline_router_predictor,
    test_baseline_router_wp2,
    two_layer_llm_predictor,
    test_two_layer_llm_router_wp2,
)
from test.digital.routers.models.laya import (
    single_layer_laya_predictor,
    test_single_layer_laya_router_wp2,
    single_layer_laya_topk_predictor,
    test_single_layer_laya_topk_router_wp2,
    two_layer_laya_predictor,
    test_two_layer_laya_router_wp2,
    two_layer_laya_topk_predictor,
    test_two_layer_laya_topk_router_wp2,
)

__all__ = [
    # LLM
    "baseline_router_predictor",
    "test_baseline_router_wp2",
    "two_layer_llm_predictor",
    "test_two_layer_llm_router_wp2",
    # LAYA
    "single_layer_laya_predictor",
    "test_single_layer_laya_router_wp2",
    "single_layer_laya_topk_predictor",
    "test_single_layer_laya_topk_router_wp2",
    "two_layer_laya_predictor",
    "test_two_layer_laya_router_wp2",
    "two_layer_laya_topk_predictor",
    "test_two_layer_laya_topk_router_wp2",
]
