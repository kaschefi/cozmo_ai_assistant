# backend/test/digital/routers/compare_routers.py
"""
Comparative Evaluation Runner across all 4 WP2 Router Architectures.

1. Baseline Monolithic LLM (test_baseline_router.py)
2. Production Two-Layer LLM (test_two_layer_llm_router.py)
3. Single-Layer LAYA Monolithic (test_single_layer_laya_router.py)
4. Two-Layer LAYA (test_two_layer_laya_router.py)

Each implementation is independently runnable and self-contained.
This script can execute all 4 or display the summary comparison table.
"""

import os
import sys

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from test.digital.routers.test_baseline_router import baseline_router_predictor
from test.digital.routers.test_two_layer_llm_router import two_layer_llm_predictor
from test.digital.routers.test_single_layer_laya_router import single_layer_laya_predictor
from test.digital.routers.test_two_layer_laya_router import two_layer_laya_predictor
from test.digital.routers.harness import evaluate_router_on_wp2


ROUTERS = [
    {
        "name": "WP2-Baseline-LLM",
        "description": "Baseline monolithic single-shot router passing all 15 tools to Ollama (qwen2.5:3b).",
        "predictor": baseline_router_predictor,
    },
    {
        "name": "WP2-Two-Layer-LLM",
        "description": "Production Two-Layer router (FastEmbed semantic reflexes + Tool RAG with Ollama).",
        "predictor": two_layer_llm_predictor,
    },
    {
        "name": "WP2-Single-Layer-Laya",
        "description": "Single-layer monolithic LAYA decision model across 15 tools.",
        "predictor": single_layer_laya_predictor,
    },
    {
        "name": "WP2-Two-Layer-Laya",
        "description": "Two-Layer architecture with FastEmbed semantic reflexes + Layer 2 LAYA.",
        "predictor": two_layer_laya_predictor,
    },
]


def run_all_comparisons():
    print("=" * 80)
    print("RUNNING ALL 4 WP2 ROUTER BENCHMARKS ON LANGSMITH")
    print("=" * 80)

    results = []
    for r in ROUTERS:
        print(f"\n>>> Running Benchmark for: {r['name']}...")
        res = evaluate_router_on_wp2(
            experiment_name=r["name"],
            predictor=r["predictor"],
            description=r["description"],
        )
        results.append(res)

    print("\n" + "=" * 90)
    print("FINAL 4-WAY ROUTER COMPARISON MATRIX (WP2 BENCHMARK)")
    print("=" * 90)
    header = f"{'Router Architecture':<24} | {'Accuracy':<14} | {'P50 (ms)':<10} | {'Mean (ms)':<10} | {'P90 (ms)':<10}"
    print(header)
    print("-" * 90)
    for res in results:
        name = res["experiment_name"]
        acc_str = f"{res['accuracy']:.1f}% ({res['correct_count']}/{res['total_count']})"
        p50 = f"{res['p50_latency_ms']:.1f}"
        mean = f"{res['mean_latency_ms']:.1f}"
        p90 = f"{res['p90_latency_ms']:.1f}"
        print(f"{name:<24} | {acc_str:<14} | {p50:<10} | {mean:<10} | {p90:<10}")
    print("=" * 90)


if __name__ == "__main__":
    run_all_comparisons()

