# backend/test/digital/routers/experiments/30_tools.py
"""
30 Tools Router Benchmark Experiment.

Evaluates ALL 6 router models on LangSmith across the 30-tools dataset:
Dataset: MoKa_Router_Benchmark_30_Tools (93 curated test cases across 30 tools + 'none')

Models Tested (from backend/test/digital/routers/models):
1. 30-Tools-2-L-Laya:       Two-Layer LAYA (FastEmbed Reflexes + Layer 2 LAYA Decision Model)
2. 30-Tools-1-L-Laya:       Single-Layer LAYA (Monolithic LAYA cross-encoder over 30 tools)
3. 30-Tools-2-L-Laya-TopK:  Two-Layer Top-K LAYA (FastEmbed Reflexes + Top-3 Tool RAG + LAYA)
4. 30-Tools-1-L-Laya-TopK:  Single-Layer Top-K LAYA (Top-3 FastEmbed Tool RAG + LAYA)
5. 30-Tools-2-L-LLM:        Production Two-Layer LLM (FastEmbed Reflexes + Tool RAG + LLM)
6. 30-Tools-Baseline-LLM:   Monolithic Single-Shot Baseline LLM across all 30 tools
"""

import os
import sys
import argparse
from typing import Dict, Any, List
from dotenv import load_dotenv

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

load_dotenv()

os.environ.setdefault("LANGCHAIN_PROJECT", "MoKa-Router-Benchmark")
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["USE_TF"] = "0"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

from test.digital.routers.harness import evaluate_router_on_benchmark, get_dataset_name_for_tools
from test.digital.routers.models import (
    get_two_layer_laya_predictor,
    get_single_layer_laya_predictor,
    get_two_layer_laya_topk_predictor,
    get_single_layer_laya_topk_predictor,
    get_two_layer_llm_predictor,
    get_baseline_router_predictor,
)

NUM_TOOLS = 30
DATASET_NAME = get_dataset_name_for_tools(NUM_TOOLS)


def run_30_tools_experiment(
    selected_model: str = "all",
    project_name: str = "MoKa-Router-Benchmark",
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    Runs the 30 Tools benchmark in LangSmith against MoKa_Router_Benchmark_30_Tools.
    Evaluates all 6 router models from test/digital/routers/models.
    """
    print("=" * 85)
    print(f"MOKA AI ASSISTANT - 30 TOOLS BENCHMARK EXPERIMENT")
    print(f"Target LangSmith Project: '{project_name}'")
    print(f"Target Dataset:          '{DATASET_NAME}' (93 test cases)")
    print(f"Selected Model Suite:    '{selected_model}'")
    print("=" * 85)

    results = []

    models_config = [
        {
            "id": "2-L-Laya",
            "name": f"{NUM_TOOLS}-Tools-2-L-Laya",
            "group": "laya",
            "description": f"Two-Layer Architecture: FastEmbed Reflexes + Layer 2 LAYA across {NUM_TOOLS} tools.",
            "get_predictor": lambda: get_two_layer_laya_predictor(num_tools=NUM_TOOLS),
        },
        {
            "id": "1-L-Laya",
            "name": f"{NUM_TOOLS}-Tools-1-L-Laya",
            "group": "laya",
            "description": f"Single-Layer Monolithic LAYA decision model directly evaluated over {NUM_TOOLS} tools.",
            "get_predictor": lambda: get_single_layer_laya_predictor(num_tools=NUM_TOOLS),
        },
        {
            "id": "2-L-Laya-TopK",
            "name": f"{NUM_TOOLS}-Tools-2-L-Laya-TopK",
            "group": "laya_topk",
            "description": f"Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 Top-3 Tool RAG with LAYA ({NUM_TOOLS} tools).",
            "get_predictor": lambda: get_two_layer_laya_topk_predictor(num_tools=NUM_TOOLS, k=3),
        },
        {
            "id": "1-L-Laya-TopK",
            "name": f"{NUM_TOOLS}-Tools-1-L-Laya-TopK",
            "group": "laya_topk",
            "description": f"Single-Layer LAYA Router with Top-3 FastEmbed Tool RAG retrieval ({NUM_TOOLS} tools).",
            "get_predictor": lambda: get_single_layer_laya_topk_predictor(num_tools=NUM_TOOLS, k=3),
        },
        {
            "id": "2-L-LLM",
            "name": f"{NUM_TOOLS}-Tools-2-L-LLM",
            "group": "llm",
            "description": f"Production Two-Layer Router: FastEmbed Reflexes + Tool RAG + LLM Classifier ({NUM_TOOLS} tools).",
            "get_predictor": lambda: get_two_layer_llm_predictor(num_tools=NUM_TOOLS),
        },
        {
            "id": "Baseline-LLM",
            "name": f"{NUM_TOOLS}-Tools-Baseline-LLM",
            "group": "llm",
            "description": f"Monolithic single-shot baseline router passing all {NUM_TOOLS} tools to LLM.",
            "get_predictor": lambda: get_baseline_router_predictor(num_tools=NUM_TOOLS),
        },
    ]

    for m in models_config:
        should_run = (
            selected_model == "all"
            or selected_model == m["id"]
            or selected_model == m["group"]
            or (selected_model == "all_laya" and m["group"] in ("laya", "laya_topk"))
        )
        if should_run:
            res = evaluate_router_on_benchmark(
                experiment_name=m["name"],
                predictor=m["get_predictor"](),
                num_tools=NUM_TOOLS,
                description=m["description"],
                force_refresh=force_refresh,
                project_name=project_name,
            )
            results.append(res)
            force_refresh = False

    if results:
        print("\n" + "=" * 90)
        print(f"BENCHMARK SUMMARY MATRIX - {NUM_TOOLS} TOOLS")
        print("=" * 90)
        header = f"{'Experiment Name':<28} | {'Accuracy':<14} | {'P50 (ms)':<10} | {'Mean (ms)':<10} | {'P90 (ms)':<10}"
        print(header)
        print("-" * 90)
        for r in results:
            name = r["experiment_name"]
            acc_str = f"{r['accuracy']:.1f}% ({r['correct_count']}/{r['total_count']})"
            p50 = f"{r['p50_latency_ms']:.1f}"
            mean = f"{r['mean_latency_ms']:.1f}"
            p90 = f"{r['p90_latency_ms']:.1f}"
            print(f"{name:<28} | {acc_str:<14} | {p50:<10} | {mean:<10} | {p90:<10}")
        print("=" * 90)
        print(f"LangSmith Project: {project_name}")
        print(f"LangSmith Dataset: {DATASET_NAME}")
        print("=" * 90 + "\n")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Run {NUM_TOOLS} Tools Benchmark on LangSmith")
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default="all",
        choices=["all", "laya", "laya_topk", "all_laya", "llm", "2-L-Laya", "1-L-Laya", "2-L-Laya-TopK", "1-L-Laya-TopK", "2-L-LLM", "Baseline-LLM"],
        help="Which model(s) to benchmark (default: 'all')"
    )
    parser.add_argument(
        "--project",
        "-p",
        type=str,
        default=os.getenv("LANGCHAIN_PROJECT", "MoKa-Router-Benchmark"),
        help="Target LangSmith project (default: MoKa-Router-Benchmark)"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-sync dataset in LangSmith"
    )
    args = parser.parse_args()

    run_30_tools_experiment(
        selected_model=args.model,
        project_name=args.project,
        force_refresh=args.force_refresh,
    )

