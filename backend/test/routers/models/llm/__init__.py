# backend/test/routers/models/llm/__init__.py
"""
LLM-based router model predictors:
- baseline: Monolithic single-shot LLM passing all tools in a single prompt
- two_layer: Two-layer architecture (FastEmbed semantic reflexes + Top-K LLM Tool RAG)
"""

from test.routers.models.llm.baseline import (
    baseline_router_predictor,
    get_baseline_router_predictor,
    test_baseline_router_wp2,
)
from test.routers.models.llm.two_layer import (
    two_layer_llm_predictor,
    get_two_layer_llm_predictor,
    test_two_layer_llm_router_wp2,
)

__all__ = [
    "baseline_router_predictor",
    "get_baseline_router_predictor",
    "test_baseline_router_wp2",
    "two_layer_llm_predictor",
    "get_two_layer_llm_predictor",
    "test_two_layer_llm_router_wp2",
]
