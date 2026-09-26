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
# 2. Predictor Runners
# -----------------------------------------------------------------------------

# --- Router Singletons for fast repeated execution ---
_TWO_LAYER_LAYA_ROUTER = None
_SINGLE_LAYER_LAYA_ROUTER = None


def get_two_layer_laya_router():
    global _TWO_LAYER_LAYA_ROUTER
    if _TWO_LAYER_LAYA_ROUTER is None:
        from test.digital.routers.test_two_layer_laya_router import TwoLayerLayaRouter
        _TWO_LAYER_LAYA_ROUTER = TwoLayerLayaRouter()
    return _TWO_LAYER_LAYA_ROUTER


def get_single_layer_laya_router():
    global _SINGLE_LAYER_LAYA_ROUTER
    if _SINGLE_LAYER_LAYA_ROUTER is None:
        from test.digital.routers.test_single_layer_laya_router import SingleLayerLayaRouter
        _SINGLE_LAYER_LAYA_ROUTER = SingleLayerLayaRouter()
    return _SINGLE_LAYER_LAYA_ROUTER


def two_layer_laya_predictor(inputs: dict) -> dict:
    """Predictor: Two-Layer Architecture with Layer 1 Reflexes + Layer 2 LAYA."""
    router = get_two_layer_laya_router()
    query = inputs["message"].strip()
    res = router.route(query)
    return {
        "route": res["route"],
        "tier": res["tier"],
        "confidence": res.get("confidence", 0.0),
        "latency_ms": res["latency_ms"],
        "pipeline": "Two-Layer (Tier 1 Reflex + Tier 2 Laya)"
    }


def single_layer_laya_predictor(inputs: dict) -> dict:
    """Predictor: Single-Layer Architecture with Monolithic LAYA across all tools."""
    router = get_single_layer_laya_router()
    query = inputs["message"].strip()
    res = router.route(query)
    return {
        "route": res["route"],
        "tier": res["tier"],
        "confidence": res.get("confidence", 0.0),
        "latency_ms": res["latency_ms"],
        "pipeline": "Single-Layer (Direct Laya - 15 Tools)"
    }


def two_layer_ollama_predictor(inputs: dict) -> dict:
    """Predictor: Production Two-Layer Architecture (Reflex + Tool RAG + Ollama qwen2.5:3b)."""
    from core.routing.layer1.semantic_layer import check_layer_1
    from core.routing.layer2.graph_nodes import tool_retrieval_node, route_query

    query = inputs["message"].strip()
    start_time = time.perf_counter()

    layer_1_route = check_layer_1(query)
    if layer_1_route:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": layer_1_route,
            "tier": "Tier 1 (Semantic Reflex)",
            "latency_ms": latency_ms,
            "pipeline": "Two-Layer (Reflex + Ollama RAG)"
        }

    state_input = {"messages": [HumanMessage(content=query)]}
    retrieval_output = tool_retrieval_node(state_input)
    state_with_tools = {**state_input, **retrieval_output}
    decision = route_query(state_with_tools)
    layer_2_route = decision.get("next_route", "none")

    latency_ms = (time.perf_counter() - start_time) * 1000
    return {
        "route": layer_2_route,
        "tier": "Tier 2 (Tool RAG + Ollama)",
        "latency_ms": latency_ms,
        "pipeline": "Two-Layer (Reflex + Ollama RAG)"
    }


def baseline_monolithic_ollama_predictor(inputs: dict) -> dict:
    """Predictor: Baseline Monolithic Prompt with Ollama qwen2.5:3b."""
    from core.routing.baseline import baseline_classify_intent

    query = inputs["message"].strip()
    start_time = time.perf_counter()

    decision = baseline_classify_intent(query)
    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "route": decision.route,
        "tier": "Monolithic (All-Tools Prompt)",
        "reasoning": decision.reasoning,
        "latency_ms": latency_ms,
        "pipeline": "Baseline (All-Tools Monolithic Ollama)"
    }


# -----------------------------------------------------------------------------
# 3. LangSmith Evaluators
# -----------------------------------------------------------------------------
def route_accuracy_evaluator(run, example) -> dict:
    """Checks whether the predicted route matches the ground truth expected route."""
    predicted_route = run.outputs.get("route", "")
    expected_route = example.outputs.get("expected_route", "")
    is_correct = (predicted_route == expected_route)
    return {
        "key": "route_accuracy",
        "score": 1.0 if is_correct else 0.0,
        "comment": f"Predicted: {predicted_route} | Expected: {expected_route}"
    }


def latency_evaluator(run, example) -> dict:
    """Records routing latency in milliseconds."""
    latency_ms = run.outputs.get("latency_ms", 0.0)
    return {
        "key": "latency_ms",
        "score": latency_ms
    }


# -----------------------------------------------------------------------------
# 4. Experiment Runner
# -----------------------------------------------------------------------------
def run_wp2_benchmark(experiment: str = "laya", force_refresh: bool = False):
    """
    Executes LangSmith evaluations under project 'WP2'.
    experiment choices:
      - 'laya': Runs Two-Layer Laya and Single-Layer Laya
      - 'ollama': Runs Two-Layer Ollama and Baseline Ollama
      - 'all': Runs all 4 router architectures
      - specific names: 'two_layer_laya', 'single_layer_laya', 'two_layer_ollama', 'baseline_ollama'
    """
    print("=" * 80)
    print("MOKA AI ASSISTANT - WP2 ROUTER BENCHMARK SUITE")
    print(f"Target LangSmith Project: '{os.environ['LANGCHAIN_PROJECT']}'")
    print(f"Target Dataset:          '{DATASET_NAME}'")
    print(f"Selected Mode:           '{experiment}'")
    print("=" * 80)

    client = Client()

    # 1. Sync dataset
    ensure_wp2_dataset_exists(client, force_refresh=force_refresh)
    examples = list(client.list_examples(dataset_name=DATASET_NAME))
    print(f"[LangSmith] Ready with {len(examples)} examples.\n")

    evaluators = [route_accuracy_evaluator, latency_evaluator]
    completed_experiments = []

    # Experiment 1: WP2-Two-Layer-Laya
    if experiment in ("laya", "all", "two_layer_laya"):
        print("-" * 80)
        print(">>> [WP2] Running Experiment: WP2-Two-Layer-Laya (Reflex + Layer 2 Laya)...")
        print("-" * 80)
        res = evaluate(
            two_layer_laya_predictor,
            data=examples,
            evaluators=evaluators,
            experiment_prefix="WP2-Two-Layer-Laya",
            max_concurrency=1,
        )
        completed_experiments.append(("WP2-Two-Layer-Laya", res))
        print("[WP2] Completed: WP2-Two-Layer-Laya\n")

    # Experiment 2: WP2-Single-Layer-Laya
    if experiment in ("laya", "all", "single_layer_laya"):
        print("-" * 80)
        print(">>> [WP2] Running Experiment: WP2-Single-Layer-Laya (Direct Laya - 15 Tools)...")
        print("-" * 80)
        res = evaluate(
            single_layer_laya_predictor,
            data=examples,
            evaluators=evaluators,
            experiment_prefix="WP2-Single-Layer-Laya",
            max_concurrency=1,
        )
        completed_experiments.append(("WP2-Single-Layer-Laya", res))
        print("[WP2] Completed: WP2-Single-Layer-Laya\n")

    # Experiment 3: WP2-Two-Layer-Ollama
    if experiment in ("ollama", "all", "two_layer_ollama"):
        print("-" * 80)
        print(">>> [WP2] Running Experiment: WP2-Two-Layer-Ollama (Reflex + Qwen2.5:3b RAG)...")
        print("-" * 80)
        res = evaluate(
            two_layer_ollama_predictor,
            data=examples,
            evaluators=evaluators,
            experiment_prefix="WP2-Two-Layer-Ollama",
            max_concurrency=1,
        )
        completed_experiments.append(("WP2-Two-Layer-Ollama", res))
        print("[WP2] Completed: WP2-Two-Layer-Ollama\n")

    # Experiment 4: WP2-Baseline-Ollama
    if experiment in ("ollama", "all", "baseline_ollama"):
        print("-" * 80)
        print(">>> [WP2] Running Experiment: WP2-Baseline-Ollama (Monolithic Qwen2.5:3b)...")
        print("-" * 80)
        res = evaluate(
            baseline_monolithic_ollama_predictor,
            data=examples,
            evaluators=evaluators,
            experiment_prefix="WP2-Baseline-Ollama",
            max_concurrency=1,
        )
        completed_experiments.append(("WP2-Baseline-Ollama", res))
        print("[WP2] Completed: WP2-Baseline-Ollama\n")

    print("=" * 80)
    print("ALL WP2 EXPERIMENTS SUBMITTED TO LANGSMITH!")
    print(f"View in LangSmith Dashboard: https://smith.langchain.com -> Project '{os.environ['LANGCHAIN_PROJECT']}'")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run WP2 Router Benchmark on LangSmith")
    parser.add_argument(
        "--experiment",
        "-e",
        type=str,
        default="laya",
        choices=["laya", "ollama", "all", "two_layer_laya", "single_layer_laya", "two_layer_ollama", "baseline_ollama"],
        help="Which experiments to run (default: 'laya')"
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-sync and recreate dataset in LangSmith"
    )
    args = parser.parse_args()
    run_wp2_benchmark(experiment=args.experiment, force_refresh=args.force_refresh)
