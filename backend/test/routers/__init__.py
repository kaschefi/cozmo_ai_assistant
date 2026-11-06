# backend/test/routers/__init__.py
"""
Routers benchmarking package for evaluating router architectures across scaling tiers:

Tiers:
- tools_20:  63 test cases across 20 tools + none
- tools_30:  93 test cases across 30 tools + none
- tools_50: 153 test cases across 50 tools + none
- tools_100: 303 test cases across 100 tools + none

Architectures:
- Two-Layer LAYA (FastEmbed reflexes + LAYA)
- Single-Layer LAYA (Monolithic LAYA cross-encoder)
- Two-Layer LAYA Top-K (FastEmbed reflexes + Tool RAG + LAYA)
- Single-Layer LAYA Top-K (Tool RAG + LAYA)
- Two-Layer LLM (FastEmbed reflexes + Tool RAG + LLM)
- Baseline Monolithic LLM
"""

from test.routers.experiments import (
    run_20_tools_experiment,
    run_30_tools_experiment,
    run_50_tools_experiment,
    run_100_tools_experiment,
)
from test.routers.harness import (
    evaluate_router_on_benchmark,
    evaluate_router_on_wp2,
    get_or_create_scaled_dataset,
    get_or_create_wp2_dataset,
    get_dataset_name_for_tools,
)
from test.routers.models import (
    single_layer_laya_predictor,
    get_single_layer_laya_predictor,
    two_layer_laya_predictor,
    get_two_layer_laya_predictor,
    single_layer_laya_topk_predictor,
    get_single_layer_laya_topk_predictor,
    two_layer_laya_topk_predictor,
    get_two_layer_laya_topk_predictor,
    baseline_router_predictor,
    two_layer_llm_predictor,
)
from test.routers.tools import (
    TOOLS_15,
    TOOLS_18,
    TOOLS_20,
    TOOLS_30,
    TOOLS_50,
    TOOLS_100,
    get_tools_preset,
)
from test.routers.benchmark_dataset import (
    BENCHMARK_TEST_CASES,
    BENCHMARK_TEST_CASES_20,
    BENCHMARK_TEST_CASES_30,
    BENCHMARK_TEST_CASES_50,
    BENCHMARK_TEST_CASES_100,
    get_benchmark_dataset,
)

__all__ = [
    "run_20_tools_experiment",
    "run_30_tools_experiment",
    "run_50_tools_experiment",
    "run_100_tools_experiment",
    "evaluate_router_on_benchmark",
    "evaluate_router_on_wp2",
    "get_or_create_scaled_dataset",
    "get_or_create_wp2_dataset",
    "get_dataset_name_for_tools",
    "single_layer_laya_predictor",
    "get_single_layer_laya_predictor",
    "two_layer_laya_predictor",
    "get_two_layer_laya_predictor",
    "single_layer_laya_topk_predictor",
    "get_single_layer_laya_topk_predictor",
    "two_layer_laya_topk_predictor",
    "get_two_layer_laya_topk_predictor",
    "baseline_router_predictor",
    "two_layer_llm_predictor",
    "TOOLS_15",
    "TOOLS_18",
    "TOOLS_20",
    "TOOLS_30",
    "TOOLS_50",
    "TOOLS_100",
    "get_tools_preset",
    "BENCHMARK_TEST_CASES",
    "BENCHMARK_TEST_CASES_20",
    "BENCHMARK_TEST_CASES_30",
    "BENCHMARK_TEST_CASES_50",
    "BENCHMARK_TEST_CASES_100",
    "get_benchmark_dataset",
]
