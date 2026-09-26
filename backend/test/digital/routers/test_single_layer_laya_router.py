# backend/test/digital/routers/test_single_layer_laya_router.py
"""
Router 3: Single-Layer Monolithic LAYA Router Evaluation (WP2 Experiment).

Implementation:
Uses the LAYA Typed Decision Model (`convaiinnovations/laya-typed-decisions`) directly
replacing the ENTIRE router pipeline (no Layer 1 reflexes, no tool RAG).
All 15 system tools are passed as typed choice criteria in a single forward pass.

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
from test.digital.routers.tools_config import TOOLS_15, build_laya_questions
from test.digital.routers.harness import evaluate_router_on_wp2

# Model singleton for fast evaluation
_LAYA_AGENT = None
_LAYA_QUESTIONS = None


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
    Evaluates a user query through the Single-Layer Monolithic LAYA Router.
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


def test_single_layer_laya_router_wp2():
    """Pytest / Test runner entrypoint."""
    results = evaluate_router_on_wp2(
        experiment_name="WP2-Single-Layer-Laya",
        predictor=single_layer_laya_predictor,
        description="Single-Layer Monolithic LAYA decision model evaluated directly over 15 tools."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="WP2-Single-Layer-Laya",
        predictor=single_layer_laya_predictor,
        description="Single-Layer Monolithic LAYA decision model evaluated directly over 15 tools."
    )
