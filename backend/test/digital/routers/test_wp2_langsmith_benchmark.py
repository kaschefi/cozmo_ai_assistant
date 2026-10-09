# backend/test/digital/routers/test_wp2_langsmith_benchmark.py
"""
LangSmith Router Benchmark & Evaluation Suite (WP2 Experiment).

Compares multiple router architectures on the official LangSmith dashboard under project 'WP2':
1. WP2-Two-Layer-Laya:       Layer 1 FastEmbed Reflexes (~6ms) + Layer 2 LAYA Decision Model
2. WP2-Single-Layer-Laya:     Monolithic Single-Shot LAYA Model across all 15 tools
3. WP2-Two-Layer-Ollama:     Layer 1 FastEmbed Reflexes + Layer 2 Tool RAG + Ollama (qwen2.5:3b)
4. WP2-Baseline-Ollama:      Monolithic Single-Shot Prompt with Ollama (qwen2.5:3b)

Evaluated via LangSmith against 'MoKa_Router_Benchmark_WP2' dataset for:
- route_accuracy: Exact match between predicted and expected action route
- latency_ms: Full routing latency per query
"""

import os
import sys
import time
import argparse
from typing import Dict, Any, List
from dotenv import load_dotenv

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Load environment variables
load_dotenv()

# Set LangSmith project for this experiment
os.environ["LANGCHAIN_PROJECT"] = "WP2"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["USE_TF"] = "0"

from langsmith import Client
from langsmith.evaluation import evaluate
from langchain_core.messages import HumanMessage

from test.digital.routers.tools_config import TOOLS_15, build_laya_questions
from test.digital.routers.benchmark_dataset import BENCHMARK_TEST_CASES

DATASET_NAME = "MoKa_Router_Benchmark_WP2"

# -----------------------------------------------------------------------------
# 1. Dataset Management
# -----------------------------------------------------------------------------
def ensure_wp2_dataset_exists(client: Client, force_refresh: bool = False) -> str:
    """
    Ensures the 48 benchmark test cases exist in the LangSmith dataset.
    Preserves existing dataset so multiple experiments can be compared side-by-side.
    """
    if client.has_dataset(dataset_name=DATASET_NAME):
        if not force_refresh:
            print(f"[LangSmith] Using existing dataset '{DATASET_NAME}'.")
            return DATASET_NAME
        print(f"[LangSmith] Re-syncing dataset '{DATASET_NAME}'...")
        client.delete_dataset(dataset_name=DATASET_NAME)

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="WP2 Router Evaluation Dataset: 48 cases comparing 2-Layer Laya, 1-Layer Laya, and Ollama routers."
    )

    for item in BENCHMARK_TEST_CASES:
        client.create_example(
            inputs={"message": item["request"]},
            outputs={
                "expected_route": item["expected_route"],
                "category": item["category"]
            },
            dataset_id=dataset.id
        )

    print(f"[LangSmith] Successfully created dataset '{DATASET_NAME}' with {len(BENCHMARK_TEST_CASES)} examples.")
    return DATASET_NAME


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 2. Modular Predictors and Experiment Runner
# -----------------------------------------------------------------------------
from test.digital.routers.two_layer_laya import two_layer_laya_predictor
from test.digital.routers.single_layer_laya import single_layer_laya_predictor
from test.digital.routers.two_layer_laya_topk import two_layer_laya_topk_predictor
from test.digital.routers.single_layer_laya_topk import single_layer_laya_topk_predictor
from test.digital.routers.two_layer_llm import two_layer_llm_predictor
from test.digital.routers.baseline_router import baseline_router_predictor
from test.digital.routers.harness import evaluate_router_on_wp2


def run_wp2_benchmark(experiment: str = "laya", force_refresh: bool = False):
    """
    Executes LangSmith evaluations under project 'WP2' using the modular router predictors.
    experiment choices:
      - 'laya': Runs Two-Layer Laya and Single-Layer Laya
      - 'laya_topk': Runs Two-Layer Laya Top-K and Single-Layer Laya Top-K
      - 'ollama': Runs Two-Layer Ollama and Baseline Ollama
      - 'all': Runs all 6 router architectures
      - specific names: '2-L-Laya', '1-L-Laya', '2-L-Laya-TopK', '1-L-Laya-TopK', '2-L-LLM', 'Baseline-LLM'
    """
    print("=" * 80)
    print("MOKA AI ASSISTANT - WP2 ROUTER BENCHMARK SUITE")
    print(f"Target LangSmith Project: '{os.environ['LANGCHAIN_PROJECT']}'")
    print(f"Target Dataset:          '{DATASET_NAME}'")
    print(f"Selected Mode:           '{experiment}'")
    print("=" * 80)

    # Experiment 1: Two-Layer LAYA (All 15 Tools)
    if experiment in ("laya", "all", "two_layer_laya", "2-L-Laya"):
        evaluate_router_on_wp2(
            experiment_name="2-L-Laya",
            predictor=two_layer_laya_predictor,
            description="Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 LAYA Decision Model across 15 tools.",
            force_refresh=force_refresh,
        )

    # Experiment 2: Single-Layer LAYA (All 15 Tools)
    if experiment in ("laya", "all", "single_layer_laya", "1-L-Laya"):
        evaluate_router_on_wp2(
            experiment_name="1-L-Laya",
            predictor=single_layer_laya_predictor,
            description="Single-Layer Monolithic LAYA decision model evaluated directly over 15 tools.",
            force_refresh=False,
        )

    # Experiment 3: Two-Layer LAYA with Top-K Tool RAG
    if experiment in ("laya_topk", "all", "two_layer_laya_topk", "2-L-Laya-TopK"):
        evaluate_router_on_wp2(
            experiment_name="2-L-Laya-TopK",
            predictor=two_layer_laya_topk_predictor,
            description="Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 Top-K Tool RAG with LAYA (k=3).",
            force_refresh=False,
        )

    # Experiment 4: Single-Layer LAYA with Top-K Tool RAG
    if experiment in ("laya_topk", "all", "single_layer_laya_topk", "1-L-Laya-TopK"):
        evaluate_router_on_wp2(
            experiment_name="1-L-Laya-TopK",
            predictor=single_layer_laya_topk_predictor,
            description="Single-Layer LAYA router with Top-K FastEmbed Tool RAG retrieval (k=3).",
            force_refresh=False,
        )

    # Experiment 5: Two-Layer LLM
    if experiment in ("ollama", "all", "two_layer_ollama", "2-L-LLM", "2-Layer-LLM"):
        evaluate_router_on_wp2(
            experiment_name="2-L-LLM",
            predictor=two_layer_llm_predictor,
            description="Production Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 Tool RAG with Ollama (qwen2.5:3b).",
            force_refresh=False,
        )

    # Experiment 6: Baseline LLM
    if experiment in ("ollama", "all", "baseline_ollama", "Baseline-LLM"):
        evaluate_router_on_wp2(
            experiment_name="Baseline-LLM",
            predictor=baseline_router_predictor,
            description="Monolithic single-shot baseline router passing all tools to LLM (qwen2.5:3b).",
            force_refresh=False,
        )

    print("=" * 80)
    print("ALL REQUESTED WP2 EXPERIMENTS COMPLETED!")
    print(f"View in LangSmith Dashboard: https://smith.langchain.com -> Project '{os.environ['LANGCHAIN_PROJECT']}'")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run WP2 Router Benchmark on LangSmith")
    parser.add_argument(
        "--experiment",
        "-e",
        type=str,
        default="all",
        choices=[
            "laya", "laya_topk", "ollama", "all",
            "two_layer_laya", "single_layer_laya",
            "two_layer_laya_topk", "single_layer_laya_topk",
            "two_layer_ollama", "baseline_ollama",
            "2-L-Laya", "1-L-Laya", "2-L-Laya-TopK", "1-L-Laya-TopK", "2-L-LLM", "Baseline-LLM"
        ],
        help="Which experiments to run (default: 'all')"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-sync and recreate dataset in LangSmith"
    )
    args = parser.parse_args()
    run_wp2_benchmark(experiment=args.experiment, force_refresh=args.force_refresh)
