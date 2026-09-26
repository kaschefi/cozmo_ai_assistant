# backend/test/digital/routers/test_two_layer_laya_router.py
"""
Router 4: Two-Layer Architecture with LAYA Router Evaluation (WP2 Experiment).

Implementation:
Uses the two-layer intelligence pipeline with LAYA:
- Layer 1: Fast deterministic FastEmbed semantic reflexes (~6ms) for physical & laptop commands.
- Layer 2: LAYA Typed Decision Model (convaiinnovations/laya-typed-decisions) replacing the LLM.
  All 15 system tools are provided directly to LAYA without top-k tool filtering.

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

import laya
from core.routing.layer1.semantic_layer import check_layer_1
from test.digital.routers.tools_config import TOOLS_15, build_laya_questions
from test.digital.routers.harness import evaluate_router_on_wp2

# Singletons for fast repeated execution
_LAYA_AGENT = None
_LAYA_QUESTIONS = None


def get_two_layer_laya_components(model_id: str = "convaiinnovations/laya-typed-decisions"):
    global _LAYA_AGENT, _LAYA_QUESTIONS
    if _LAYA_AGENT is None:
        print("[TwoLayerLaya] Initializing Layer 1 Reflexes and Layer 2 LAYA...")
        _ = check_layer_1("warmup")
        _LAYA_AGENT = laya.load(model_id)
        _LAYA_QUESTIONS = build_laya_questions(TOOLS_15)
        _ = _LAYA_AGENT.predict("warmup", _LAYA_QUESTIONS)
        print("[TwoLayerLaya] Two-Layer LAYA router ready.\n")
    return _LAYA_AGENT, _LAYA_QUESTIONS


def two_layer_laya_predictor(inputs: dict) -> dict:
    """
    Evaluates a user query through the Two-Layer LAYA Router (Reflex + Layer 2 LAYA).
    """
    agent, questions = get_two_layer_laya_components()
    query = inputs["message"].strip()
    start_time = time.perf_counter()

    # Step 1: Check Layer 1 Semantic Reflexes
    layer_1_route = check_layer_1(query)
    if layer_1_route:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": layer_1_route,
            "tier": "Tier 1 (Semantic Reflex)",
            "latency_ms": latency_ms,
            "pipeline": "Two-Layer (Tier 1 FastEmbed Reflex)"
        }

    # Step 2: Fall back to Layer 2 LAYA Decision Model across 15 tools
    result = agent.predict(query, questions)
    answers = result.get("answers", result)
    decision = answers.get("tool_selection", {})

    selected_route = decision.get("choice", "none")
    confidence = decision.get("confidence", 0.0)
    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "route": selected_route,
        "tier": "Tier 2 (LAYA Decision Model)",
        "confidence": confidence,
        "latency_ms": latency_ms,
        "probabilities": decision.get("probabilities", {}),
        "pipeline": "Two-Layer (Tier 2 LAYA Model - 15 Tools)"
    }


def test_two_layer_laya_router_wp2():
    """Pytest / Test runner entrypoint."""
    results = evaluate_router_on_wp2(
        experiment_name="WP2-Two-Layer-Laya",
        predictor=two_layer_laya_predictor,
        description="Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 LAYA Decision Model across 15 tools."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="WP2-Two-Layer-Laya",
        predictor=two_layer_laya_predictor,
        description="Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 LAYA Decision Model across 15 tools."
    )
