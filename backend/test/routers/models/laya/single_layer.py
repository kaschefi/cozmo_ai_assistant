# backend/test/routers/models/laya/single_layer.py
"""
Router: Single-Layer Monolithic LAYA Router Evaluation.

Implementation:
Uses the LAYA Typed Decision Model (`convaiinnovations/laya-typed-decisions`) directly
replacing the ENTIRE router pipeline (no Layer 1 reflexes, no tool RAG).
All system tools (15, 20, 30, 50, 100) are passed as typed choice criteria in a single forward pass.
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
from test.routers.tools import TOOLS_15, build_laya_questions, get_tools_preset
from test.routers.harness import evaluate_router_on_wp2, evaluate_router_on_benchmark

# Model singleton for fast evaluation
_LAYA_AGENT = None
_LAYA_QUESTIONS = None
_PREDICTOR_CACHE: Dict[int, Callable[[dict], dict]] = {}


def get_laya_agent(model_id: str = "convaiinnovations/laya-typed-decisions"):
    global _LAYA_AGENT, _LAYA_QUESTIONS
    if _LAYA_AGENT is None:
        print(f"[SingleLayerLaya] Loading LAYA model ({model_id})...")
        _LAYA_AGENT = laya.load(model_id)
        _LAYA_QUESTIONS = build_laya_questions(TOOLS_15)
        # Warmup pass
        _ = _LAYA_AGENT.predict("warmup", _LAYA_QUESTIONS)
        print("[SingleLayerLaya] LAYA model ready.\n")
    return _LAYA_AGENT, _LAYA_QUESTIONS


def single_layer_laya_predictor(inputs: dict) -> dict:
    """
    Evaluates a user query through the Single-Layer Monolithic LAYA Router (15 tools).
    """
    agent, questions = get_laya_agent()
    query = inputs["message"].strip()
    start_time = time.perf_counter()

    result = agent.predict(query, questions)
    answers = result.get("answers", result)
    decision = answers.get("tool_selection", {})

    selected_route = decision.get("choice", "none")
    confidence = decision.get("confidence", 0.0)
    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "route": selected_route,
        "confidence": confidence,
        "latency_ms": latency_ms,
        "probabilities": decision.get("probabilities", {}),
        "pipeline": "Single-Layer (Direct LAYA - 15 Tools)"
    }


def get_single_layer_laya_predictor(
    num_tools: int = 20,
    model_id: str = "convaiinnovations/laya-typed-decisions"
) -> Callable[[dict], dict]:
    """
    Returns a configured predictor callable for N tools (20, 30, 50, 100)
    evaluating queries monolithically through LAYA without reflexes or RAG.
    """
    global _PREDICTOR_CACHE, _LAYA_AGENT
    if num_tools in _PREDICTOR_CACHE:
        return _PREDICTOR_CACHE[num_tools]

    if _LAYA_AGENT is None:
        print(f"[SingleLayerLaya] Loading LAYA model ({model_id})...")
        _LAYA_AGENT = laya.load(model_id)

    tools_dict = get_tools_preset(num_tools)
    questions = build_laya_questions(tools_dict)
    _ = _LAYA_AGENT.predict("warmup", questions)
    print(f"[SingleLayerLaya] Ready for {num_tools} Tools evaluation.\n")

    def scaled_predictor(inputs: dict) -> dict:
        query = inputs["message"].strip()
        start_time = time.perf_counter()

        result = _LAYA_AGENT.predict(query, questions)
        answers = result.get("answers", result)
        decision = answers.get("tool_selection", {})

        selected_route = decision.get("choice", "none")
        confidence = decision.get("confidence", 0.0)
        latency_ms = (time.perf_counter() - start_time) * 1000

        return {
            "route": selected_route,
            "confidence": confidence,
            "latency_ms": latency_ms,
            "probabilities": decision.get("probabilities", {}),
            "pipeline": f"Single-Layer (Direct LAYA - {num_tools} Tools)"
        }

    _PREDICTOR_CACHE[num_tools] = scaled_predictor
    return scaled_predictor


class SingleLayerLayaRouter:
    """Class wrapper around single_layer_laya_predictor for backward compatibility."""
    def __init__(self, num_tools: int = 20):
        self._predictor = get_single_layer_laya_predictor(num_tools)

    def route(self, query: str) -> dict:
        return self._predictor({"message": query})


def test_single_layer_laya_router_wp2():
    """Pytest / Test runner entrypoint."""
    results = evaluate_router_on_wp2(
        experiment_name="1-L-Laya",
        predictor=single_layer_laya_predictor,
        description="Single-Layer Monolithic LAYA decision model evaluated directly over 15 tools."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="1-L-Laya",
        predictor=single_layer_laya_predictor,
        description="Single-Layer Monolithic LAYA decision model evaluated directly over 15 tools."
    )
