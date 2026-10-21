# backend/test/digital/routers/models/laya/__init__.py
"""
LAYA-based decision model router predictors:
- single_layer: Monolithic LAYA evaluating all tools in a single forward pass
- single_layer_topk: Single-Layer LAYA evaluating only Top-K retrieved candidates
- two_layer: Two-Layer architecture (FastEmbed reflexes + LAYA across all tools)
- two_layer_topk: Production Two-Layer Top-K LAYA (FastEmbed reflexes + Top-K LAYA)
"""

from test.digital.routers.models.laya.single_layer import (
    single_layer_laya_predictor,
    test_single_layer_laya_router_wp2,
)
from test.digital.routers.models.laya.single_layer_topk import (
    single_layer_laya_topk_predictor,
    test_single_layer_laya_topk_router_wp2,
)
from test.digital.routers.models.laya.two_layer import (
    two_layer_laya_predictor,
    test_two_layer_laya_router_wp2,
)
from test.digital.routers.models.laya.two_layer_topk import (
    two_layer_laya_topk_predictor,
    test_two_layer_laya_topk_router_wp2,
)

__all__ = [
    "single_layer_laya_predictor",
    "test_single_layer_laya_router_wp2",
    "single_layer_laya_topk_predictor",
    "test_single_layer_laya_topk_router_wp2",
    "two_layer_laya_predictor",
    "test_two_layer_laya_router_wp2",
    "two_layer_laya_topk_predictor",
    "test_two_layer_laya_topk_router_wp2",
]
