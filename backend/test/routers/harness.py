# backend/test/routers/harness.py
"""
Evaluation Harness for Router Benchmarking (Local & Offline Capable).

Provides a unified, fast evaluation pipeline that tests any router implementation
against standardized datasets (WP2, 20 tools, 30 tools, 50 tools, 100 tools)
directly without requiring external LangSmith trace ingestion.

Supports:
- Offline local execution with zero network requirement.
- Tracking accuracy, P50/Mean/P90 latency, category breakdowns, and LLM token usage.
- Optional LangSmith logging if explicitly enabled.
- Automatic integration with `saver.py` and `bar_chart.py`.
"""

import os
import sys
import time
import statistics
from typing import Callable, Dict, Any, List, Optional
from dotenv import load_dotenv

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

load_dotenv()

# Global configuration defaults
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["USE_TF"] = "0"

from test.routers.benchmark_dataset import BENCHMARK_TEST_CASES, get_benchmark_dataset
from test.routers.saver import save_experiment_result
from test.routers.bar_chart import generate_bar_chart_for_tools

WP2_DATASET_NAME = "MoKa_Router_Benchmark_WP2"
DATASET_NAME = WP2_DATASET_NAME


def get_dataset_name_for_tools(num_tools: int) -> str:
    """Returns standardized dataset name for N tools."""
    return f"MoKa_Router_Benchmark_{num_tools}_Tools"


def get_or_create_scaled_dataset(client=None, num_tools: int = 20, force_refresh: bool = False) -> List[Any]:
    """Compatibility shim returning local benchmark dataset without hitting LangSmith."""
    return get_benchmark_dataset(num_tools)


def get_or_create_wp2_dataset(client=None, force_refresh: bool = False) -> List[Any]:
    """Compatibility shim returning local WP2 benchmark dataset."""
    return BENCHMARK_TEST_CASES


def _run_local_evaluation_pipeline(
    experiment_name: str,
    predictor: Callable[[dict], dict],
    test_cases: List[Dict[str, Any]],
    dataset_name: str,
    num_tools: int,
    description: str = "",
    phase: str = "phase3",
    auto_save: bool = True,
    auto_chart: bool = True,
) -> Dict[str, Any]:
    """
    Executes benchmark evaluation locally over test cases, collecting metrics
    without hitting LangSmith API rate limits.
    """
    total_count = len(test_cases)
    print(f"\n[Harness] Starting evaluation for '{experiment_name}' across {total_count} test cases...")

    correct_count = 0
    latencies = []
    category_breakdown = {}
    total_tokens = 0
    predictions_log = []

    start_eval_time = time.perf_counter()

    for idx, test_case in enumerate(test_cases, 1):
        # Support both {"inputs": {"message": ...}} and {"request": ...}
        if "inputs" in test_case:
            query = test_case["inputs"].get("message", "")
        else:
            query = test_case.get("request", "")

        # Support both {"outputs": {"expected_route": ...}} and direct keys
        if "outputs" in test_case:
            expected = test_case["outputs"].get("expected_route", "")
            category = test_case["outputs"].get("category", "general")
        else:
            expected = test_case.get("expected_route", "")
            category = test_case.get("category", "general")

        pred_res = predictor({"message": query})

        predicted_route = pred_res.get("route", "")
        latency = float(pred_res.get("latency_ms", 0.0))
        tokens_used = int(pred_res.get("tokens_used", pred_res.get("total_tokens", 0)))
        total_tokens += tokens_used

        is_correct = (predicted_route == expected)
        if is_correct:
            correct_count += 1

        latencies.append(latency)
        if category not in category_breakdown:
            category_breakdown[category] = {"correct": 0, "total": 0}
        category_breakdown[category]["total"] += 1
        if is_correct:
            category_breakdown[category]["correct"] += 1

        predictions_log.append({
            "query": query,
            "expected": expected,
            "predicted": predicted_route,
            "is_correct": is_correct,
            "latency_ms": latency,
            "category": category,
            "tokens_used": tokens_used,
            "pipeline": pred_res.get("pipeline", ""),
        })

    total_eval_duration = (time.perf_counter() - start_eval_time)

    accuracy = (correct_count / total_count * 100.0) if total_count > 0 else 0.0
    p50_latency = statistics.median(latencies) if latencies else 0.0
    mean_latency = statistics.mean(latencies) if latencies else 0.0
    p90_latency = sorted(latencies)[int(0.9 * len(latencies))] if latencies else 0.0
    min_lat = min(latencies) if latencies else 0.0
    max_lat = max(latencies) if latencies else 0.0

    # Token per call statistics
    non_zero_tokens = [p["tokens_used"] for p in predictions_log if p.get("tokens_used", 0) > 0]
    llm_calls_count = len(non_zero_tokens)
    avg_tokens_per_call = round(sum(non_zero_tokens) / llm_calls_count, 1) if llm_calls_count > 0 else 0.0
    avg_tokens_per_query = round(total_tokens / total_count, 1) if total_count > 0 else 0.0

    print("\n" + "=" * 80)
    print(f"EXPERIMENT RESULTS: {experiment_name}")
    print("=" * 80)
    print(f"Overall Accuracy:       {correct_count}/{total_count} ({accuracy:.1f}%)")
    print(f"Median Latency:         {p50_latency:.1f} ms")
    print(f"Mean Latency:           {mean_latency:.1f} ms")
    print(f"P90 Latency:            {p90_latency:.1f} ms")
    print(f"Latency Range:          {min_lat:.1f} ms - {max_lat:.1f} ms")
    print(f"Total Tokens Used:      {total_tokens:,}")
    print(f"LLM Calls:              {llm_calls_count}/{total_count}")
    print(f"Avg Tokens Per Call:    {avg_tokens_per_call}")
    print(f"Avg Tokens Per Query:   {avg_tokens_per_query}")
    print(f"Evaluation Time:        {total_eval_duration:.2f} s")
    print("-" * 80)
    print("Category Accuracy:")
    for cat, stats in sorted(category_breakdown.items()):
        cat_acc = (stats["correct"] / stats["total"] * 100) if stats["total"] else 0
        print(f"  - {cat:<18}: {stats['correct']}/{stats['total']} ({cat_acc:.1f}%)")
    print("-" * 80)
    print(f"Dataset Name:           '{dataset_name}'")
    print("=" * 80 + "\n")

    result_dict = {
        "experiment_name": experiment_name,
        "model_id": experiment_name,
        "num_tools": num_tools,
        "phase": phase,
        "accuracy": accuracy,
        "correct_count": correct_count,
        "total_count": total_count,
        "p50_latency_ms": p50_latency,
        "mean_latency_ms": mean_latency,
        "p90_latency_ms": p90_latency,
        "min_latency_ms": min_lat,
        "max_latency_ms": max_lat,
        "total_tokens": total_tokens,
        "llm_calls_count": llm_calls_count,
        "avg_tokens_per_call": avg_tokens_per_call,
        "avg_tokens_per_query": avg_tokens_per_query,
        "category_breakdown": category_breakdown,
        "dataset_name": dataset_name,
        "description": description,
        "predictions": predictions_log,
    }

    # Automatically persist to JSON in backend/data/router results/<phase>/
    if auto_save:
        save_experiment_result(result_dict, num_tools=num_tools, phase=phase)

    # Automatically generate / refresh the comparative bar chart in docs/charts/<phase>/
    if auto_chart:
        try:
            generate_bar_chart_for_tools(num_tools=num_tools, phase=phase)
        except Exception as e:
            print(f"[Harness] Warning: could not generate bar chart: {e}")

    return result_dict


def evaluate_router_on_wp2(
    experiment_name: str,
    predictor: Callable[[dict], dict],
    description: str = "",
    force_refresh: bool = False,
    phase: str = "phase3",
) -> Dict[str, Any]:
    """Backward-compatible runner for WP2 15-tool benchmark."""
    print("=" * 80)
    print(f"WP2 BENCHMARK: {experiment_name}")
    if description:
        print(f"Description: {description}")
    print(f"Target Dataset:          '{WP2_DATASET_NAME}'")
    print("=" * 80)

    test_cases = BENCHMARK_TEST_CASES
    return _run_local_evaluation_pipeline(
        experiment_name=experiment_name,
        predictor=predictor,
        test_cases=test_cases,
        dataset_name=WP2_DATASET_NAME,
        num_tools=15,
        description=description,
        phase=phase,
    )


def evaluate_router_on_benchmark(
    experiment_name: str,
    predictor: Callable[[dict], dict],
    num_tools: int = 20,
    description: str = "",
    force_refresh: bool = False,
    project_name: Optional[str] = None,
    phase: str = "phase3",
    auto_save: bool = True,
    auto_chart: bool = True,
) -> Dict[str, Any]:
    """
    Standardized abstract evaluation runner for Scaled Tool Benchmarks (N = 20, 30, 50, 100):
    1. Loads the standardized N-tools dataset from local benchmark suite.
    2. Runs evaluation locally on the given predictor.
    3. Computes summary metrics (Accuracy, P50, Mean, P90, Min/Max latency, Token Usage).
    4. Automatically saves JSON to `backend/data/router results/<phase>/`.
    5. Automatically generates/updates the bar chart in `docs/charts/<phase>/`.
    """
    dataset_name = get_dataset_name_for_tools(num_tools)

    print("=" * 80)
    print(f"BENCHMARK EXPERIMENT: {experiment_name}")
    if description:
        print(f"Description: {description}")
    print(f"Number of Tools:         {num_tools}")
    print(f"Target Dataset:          '{dataset_name}'")
    print(f"Phase:                   '{phase}'")
    print("=" * 80)

    test_cases = get_benchmark_dataset(num_tools)
    return _run_local_evaluation_pipeline(
        experiment_name=experiment_name,
        predictor=predictor,
        test_cases=test_cases,
        dataset_name=dataset_name,
        num_tools=num_tools,
        description=description,
        phase=phase,
        auto_save=auto_save,
        auto_chart=auto_chart,
    )
