# backend/test/digital/routers/harness.py
"""
Abstract LangSmith Evaluation Harness for Router Benchmarking.

Provides a unified, reusable evaluation pipeline that tests any router implementation
against the fixed 'MoKa_Router_Benchmark_WP2' dataset and automatically submits the
experiment to LangSmith under project 'WP2'.
"""

import os
import sys
import time
import statistics
from typing import Callable, Dict, Any, List
from dotenv import load_dotenv

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

load_dotenv()

# Global configuration for WP2
os.environ["LANGCHAIN_PROJECT"] = "WP2"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["USE_TF"] = "0"

from langsmith import Client
from langsmith.evaluation import evaluate
from test.digital.routers.benchmark_dataset import BENCHMARK_TEST_CASES

DATASET_NAME = "MoKa_Router_Benchmark_WP2"


def get_or_create_wp2_dataset(client: Client, force_refresh: bool = False) -> List[Any]:
    """
    Ensures the fixed WP2 dataset exists in LangSmith and returns all examples.
    Preserves the existing dataset so all experiments attach to the same dataset.
    """
    if client.has_dataset(dataset_name=DATASET_NAME):
        if not force_refresh:
            examples = list(client.list_examples(dataset_name=DATASET_NAME))
            if len(examples) == len(BENCHMARK_TEST_CASES):
                return examples
        client.delete_dataset(dataset_name=DATASET_NAME)

    print(f"[Harness] Creating fixed LangSmith dataset '{DATASET_NAME}' ({len(BENCHMARK_TEST_CASES)} examples)...")
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Fixed WP2 Router Benchmark: 48 curated cases across 15 tools + chat fallback."
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

    examples = list(client.list_examples(dataset_name=DATASET_NAME))
    print(f"[Harness] Dataset '{DATASET_NAME}' successfully registered with {len(examples)} examples.\n")
    return examples


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


def evaluate_router_on_wp2(
    experiment_name: str,
    predictor: Callable[[dict], dict],
    description: str = "",
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Standardized abstract evaluation runner:
    1. Loads the fixed WP2 dataset from LangSmith.
    2. Runs evaluation on the given predictor.
    3. Computes summary metrics (Accuracy, P50, Mean, P90, Min/Max latency).
    4. Automatically logs the experiment into LangSmith project 'WP2'.
    5. Displays formatted results and direct dashboard URLs.
    """
    print("=" * 80)
    print(f"WP2 BENCHMARK: {experiment_name}")
    if description:
        print(f"Description: {description}")
    print(f"Target LangSmith Project: '{os.environ['LANGCHAIN_PROJECT']}'")
    print(f"Target Dataset:          '{DATASET_NAME}'")
    print("=" * 80)

    client = Client()
    examples = get_or_create_wp2_dataset(client, force_refresh=force_refresh)

    evaluators = [route_accuracy_evaluator, latency_evaluator]

    print(f"\n[Harness] Starting evaluation for '{experiment_name}' across {len(examples)} test cases...")
    eval_results = evaluate(
        predictor,
        data=examples,
        evaluators=evaluators,
        experiment_prefix=experiment_name,
        max_concurrency=1,
    )

    # Extract results directly from the evaluated rows for reliable, instantaneous metrics
    rows = list(eval_results)
    total_count = len(rows) if rows else len(examples)
    correct_count = 0
    latencies = []
    category_breakdown = {}

    for row in rows:
        run = row.get("run")
        example = row.get("example")
        if not run or not example:
            continue
        predicted = (run.outputs or {}).get("route", "")
        expected = (example.outputs or {}).get("expected_route", "")
        category = (example.outputs or {}).get("category", "unknown")
        latency = float((run.outputs or {}).get("latency_ms", 0.0))

        is_correct = (predicted == expected)
        if is_correct:
            correct_count += 1

        latencies.append(latency)
        if category not in category_breakdown:
            category_breakdown[category] = {"correct": 0, "total": 0}
        category_breakdown[category]["total"] += 1
        if is_correct:
            category_breakdown[category]["correct"] += 1

    accuracy = (correct_count / total_count * 100.0) if total_count > 0 else 0.0
    p50_latency = statistics.median(latencies) if latencies else 0.0
    mean_latency = statistics.mean(latencies) if latencies else 0.0
    p90_latency = sorted(latencies)[int(0.9 * len(latencies))] if latencies else 0.0
    min_lat = min(latencies) if latencies else 0.0
    max_lat = max(latencies) if latencies else 0.0

    experiment_url = getattr(eval_results, "url", f"https://smith.langchain.com (Project '{os.environ['LANGCHAIN_PROJECT']}')")

    print("\n" + "=" * 80)
    print(f"EXPERIMENT RESULTS: {experiment_name}")
    print("=" * 80)
    print(f"Overall Accuracy:  {correct_count}/{total_count} ({accuracy:.1f}%)")
    print(f"Median Latency:    {p50_latency:.1f} ms")
    print(f"Mean Latency:      {mean_latency:.1f} ms")
    print(f"P90 Latency:       {p90_latency:.1f} ms")
    print(f"Latency Range:     {min_lat:.1f} ms - {max_lat:.1f} ms")
    print("-" * 80)
    print("Category Accuracy:")
    for cat, stats in sorted(category_breakdown.items()):
        cat_acc = (stats["correct"] / stats["total"] * 100) if stats["total"] else 0
        print(f"  - {cat:<18}: {stats['correct']}/{stats['total']} ({cat_acc:.1f}%)")
    print("-" * 80)
    print(f"LangSmith Project: '{os.environ['LANGCHAIN_PROJECT']}'")
    print(f"Experiment URL:    {experiment_url}")
    print("=" * 80 + "\n")

    return {
        "experiment_name": experiment_name,
        "accuracy": accuracy,
        "correct_count": correct_count,
        "total_count": total_count,
        "p50_latency_ms": p50_latency,
        "mean_latency_ms": mean_latency,
        "p90_latency_ms": p90_latency,
        "category_breakdown": category_breakdown,
        "experiment_url": experiment_url,
        "eval_results": eval_results,
    }
