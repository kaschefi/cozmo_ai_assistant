# backend/test/routers/models/laya/two_layer.py
"""
Router: Two-Layer Architecture with LAYA Router Evaluation.

Implementation:
Uses the two-layer intelligence pipeline with LAYA:
- Layer 1: Fast deterministic FastEmbed semantic reflexes (~6ms) for physical & laptop commands.
- Layer 2: LAYA Typed Decision Model (convaiinnovations/laya-typed-decisions) replacing the LLM.
  All active system tools (15, 20, 30, 50, 100) are provided directly to LAYA without top-k tool filtering.
"""

import os
import sys
import time
from typing import Callable, Dict, Any, Optional

# Ensure backend directory is in path (5 levels up from models/laya/)
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import laya
from core.routing.layer1.semantic_layer import check_layer_1
from test.routers.tools import TOOLS_15, TOOLS_20, build_laya_questions, get_tools_preset
from test.routers.harness import evaluate_router_on_wp2, evaluate_router_on_benchmark

# Singletons for fast repeated execution
_LAYA_AGENT = None
_LAYA_QUESTIONS = None
_PREDICTOR_CACHE: Dict[int, Callable[[dict], dict]] = {}


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
    Evaluates a user query through the default Two-Layer LAYA Router (15 tools).
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

    # Step 2: Fall back to Layer 2 LAYA Decision Model across tools
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


def get_two_layer_laya_predictor(
    num_tools: int = 20,
    model_id: str = "convaiinnovations/laya-typed-decisions"
) -> Callable[[dict], dict]:
    """
    Returns a configured predictor callable for N tools (20, 30, 50, 100)
    with Layer 1 reflexes and full Layer 2 LAYA choice criteria.
    """
    global _PREDICTOR_CACHE, _LAYA_AGENT
    if num_tools in _PREDICTOR_CACHE:
        return _PREDICTOR_CACHE[num_tools]

    print(f"[TwoLayerLaya] Initializing Layer 1 Reflexes and Layer 2 LAYA ({num_tools} Tools)...")
    _ = check_layer_1("warmup")
    if _LAYA_AGENT is None:
        _LAYA_AGENT = laya.load(model_id)

    tools_dict = get_tools_preset(num_tools)
    questions = build_laya_questions(tools_dict)
    _ = _LAYA_AGENT.predict("warmup", questions)
    print(f"[TwoLayerLaya] Ready for {num_tools} Tools evaluation.\n")

    def scaled_predictor(inputs: dict) -> dict:
        query = inputs["message"].strip()
        start_time = time.perf_counter()

        # Step 1: Check Layer 1 Semantic Reflexes (~6ms deterministic match)
        layer_1_route = check_layer_1(query)
        if layer_1_route and (layer_1_route in tools_dict or layer_1_route == "none"):
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "route": layer_1_route,
                "tier": "Tier 1 (Semantic Reflex)",
                "latency_ms": latency_ms,
                "pipeline": "Two-Layer (Tier 1 FastEmbed Reflex)"
            }

        # Step 2: Fall back to Layer 2 LAYA Decision Model across N tools
        result = _LAYA_AGENT.predict(query, questions)
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
            "pipeline": f"Two-Layer (Tier 2 LAYA Model - {num_tools} Tools)"
        }

    _PREDICTOR_CACHE[num_tools] = scaled_predictor
    return scaled_predictor


class TwoLayerLayaRouter:
    """Class wrapper around two_layer_laya_predictor for backward compatibility."""
    def __init__(self, num_tools: int = 20):
        self._predictor = get_two_layer_laya_predictor(num_tools)

    def route(self, query: str) -> dict:
        return self._predictor({"message": query})


def test_two_layer_laya_router_wp2():
    """Pytest / Test runner entrypoint for WP2."""
    results = evaluate_router_on_wp2(
        experiment_name="2-L-Laya",
        predictor=two_layer_laya_predictor,
        description="Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 LAYA Decision Model across 15 tools."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="2-L-Laya",
        predictor=two_layer_laya_predictor,
        description="Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 LAYA Decision Model across 15 tools."
    )
