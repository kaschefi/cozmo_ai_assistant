# backend/test/digital/routers/test_baseline_router.py
"""
Router 1: Baseline Monolithic LLM Router Evaluation (WP2 Experiment).

Implementation:
Uses the monolithic single-shot baseline LLM router from `backend/core/routing/baseline`.
All 15 system tools and full descriptions are passed directly to the LLM (qwen2.5:3b)
in a single prompt without Layer 1 reflexes or vector RAG.

Running this file automatically executes the benchmark and adds the run to the
'WP2' experiment in the LangSmith dashboard.
"""

import os
import sys
import time

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from core.routing.baseline import baseline_classify_intent
from test.digital.routers.harness import evaluate_router_on_wp2


_BASELINE_INITIALIZED = False


def ensure_baseline_warm():
    global _BASELINE_INITIALIZED
    if not _BASELINE_INITIALIZED:
        print("[BaselineLLM] Warming up Ollama LLM...")
        _ = baseline_classify_intent("warmup")
        _BASELINE_INITIALIZED = True
        print("[BaselineLLM] Warmup complete.\n")


def baseline_router_predictor(inputs: dict) -> dict:
    """
    Evaluates a user query through the Baseline Monolithic LLM Router.
    """
    ensure_baseline_warm()
    query = inputs["message"].strip()
    start_time = time.perf_counter()

    decision = baseline_classify_intent(query)
    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "route": decision.route,
        "reasoning": decision.reasoning or "",
        "latency_ms": latency_ms,
        "pipeline": "Baseline (Monolithic All-Tools LLM)"
    }


def test_baseline_router_wp2():
    """Pytest / Test runner entrypoint."""
    results = evaluate_router_on_wp2(
        experiment_name="WP2-Baseline-LLM",
        predictor=baseline_router_predictor,
        description="Monolithic single-shot baseline router passing all tools to LLM (qwen2.5:3b)."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="WP2-Baseline-LLM",
        predictor=baseline_router_predictor,
        description="Monolithic single-shot baseline router passing all tools to LLM (qwen2.5:3b)."
    )
