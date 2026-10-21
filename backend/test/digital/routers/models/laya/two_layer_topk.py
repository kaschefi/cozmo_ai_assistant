# backend/test/digital/routers/models/laya/two_layer_topk.py
"""
Router 6: Two-Layer Architecture with Top-K LAYA Router Evaluation (WP2 Experiment).

Implementation:
Uses the two-layer intelligence pipeline combining fast reflexes with Top-K LAYA:
- Layer 1: Fast deterministic FastEmbed semantic reflexes (~6ms) for physical & system reflex commands.
  If an utterance matches a reflex threshold, routes instantly without invoking Layer 2.
- Layer 2: FastEmbed FAISS Tool Vector Store retrieves only the top-k most semantically relevant
  candidate tools (default k=3).
  - If no tools pass the similarity threshold, falls back to conversational "none".
  - If candidate tools match, dynamically passes ONLY those top-k tools (plus "none") as
    typed choice criteria into the LAYA Typed Decision Model (`convaiinnovations/laya-typed-decisions`).

Running this file automatically executes the benchmark and adds the run to the
'WP2' experiment in the LangSmith dashboard.
"""

import os
import sys
import time
from typing import Dict, Any

# Ensure backend directory is in path (5 levels up from models/laya/)
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import laya
from core.routing.layer1.semantic_layer import check_layer_1
from core.routing.layer2.tool_vector_db import tool_rag_registry
from test.digital.routers.tools import TOOLS_15, build_laya_questions
from test.digital.routers.harness import evaluate_router_on_wp2

# Singletons for fast repeated evaluation
_LAYA_AGENT = None
_TWO_LAYER_TOPK_INITIALIZED = False


def ensure_two_layer_laya_topk_ready(model_id: str = "convaiinnovations/laya-typed-decisions"):
    """Initializes Layer 1 semantic reflexes, Layer 2 Tool RAG index, and LAYA decision model."""
    global _LAYA_AGENT, _TWO_LAYER_TOPK_INITIALIZED
    if not _TWO_LAYER_TOPK_INITIALIZED:
        print(f"[TwoLayerLayaTopK] Initializing Layer 1 Reflexes and Layer 2 Top-K LAYA ({model_id})...")
        # Initialize Layer 1 reflexes (which also builds tool_rag_registry)
        _ = check_layer_1("warmup")

        if _LAYA_AGENT is None:
            _LAYA_AGENT = laya.load(model_id)

        # Warmup pass with sample top-k criteria
        sample_tools = tool_rag_registry.search_relevant_tools("warmup", k=3)
        sample_dict = {t["name"]: t["description"] for t in sample_tools}
        sample_dict["none"] = TOOLS_15["none"]
        _ = _LAYA_AGENT.predict("warmup", build_laya_questions(sample_dict))

        _TWO_LAYER_TOPK_INITIALIZED = True
        print("[TwoLayerLayaTopK] Router ready.\n")
    return _LAYA_AGENT


def two_layer_laya_topk_predictor(inputs: dict, k: int = 3) -> dict:
    """
    Evaluates a user query through Two-Layer Router with Top-K LAYA.
    
    Step 1: Check Layer 1 Semantic Reflexes.
    Step 2: If Layer 1 misses, query Tool RAG for top-k candidates and classify via LAYA.
    """
    agent = ensure_two_layer_laya_topk_ready()
    query = inputs["message"].strip()
    start_time = time.perf_counter()

    # Step 1: Check Layer 1 Semantic Reflexes (~6ms deterministic match)
    layer_1_route = check_layer_1(query)
    if layer_1_route:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": layer_1_route,
            "tier": "Tier 1 (Semantic Reflex)",
            "latency_ms": latency_ms,
            "pipeline": "Two-Layer (Tier 1 FastEmbed Reflex)"
        }

    # Step 2: Fall back to Layer 2 Tool RAG + LAYA Decision Model
    matched_tools = tool_rag_registry.search_relevant_tools(query, k=k)

    # If no tools passed similarity threshold, bypass LAYA and return "none"
    if not matched_tools:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": "none",
            "tier": "Tier 2 (Tool RAG + LAYA)",
            "confidence": 1.0,
            "latency_ms": latency_ms,
            "probabilities": {"none": 1.0},
            "top_k_candidates": [],
            "pipeline": f"Two-Layer (Tier 2 Top-{k} Tool RAG + LAYA)"
        }

    # Dynamically construct choice criteria for ONLY the retrieved top-k tools + "none"
    tools_dict = {tool["name"]: tool["description"] for tool in matched_tools}
    tools_dict["none"] = TOOLS_15["none"]
    questions = build_laya_questions(tools_dict)

    result = agent.predict(query, questions)
    answers = result.get("answers", result)
    decision = answers.get("tool_selection", {})

    selected_route = decision.get("choice", "none")
    confidence = decision.get("confidence", 0.0)
    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "route": selected_route,
        "tier": "Tier 2 (Tool RAG + LAYA)",
        "confidence": confidence,
        "latency_ms": latency_ms,
        "probabilities": decision.get("probabilities", {}),
        "top_k_candidates": [t["name"] for t in matched_tools],
        "pipeline": f"Two-Layer (Tier 2 Top-{k} Tool RAG + LAYA)"
    }


class TwoLayerLayaTopKRouter:
    """Class wrapper around two_layer_laya_topk_predictor for backward compatibility."""
    def __init__(self, k: int = 3):
        self.k = k

    def route(self, query: str) -> dict:
        return two_layer_laya_topk_predictor({"message": query}, k=self.k)


def test_two_layer_laya_topk_router_wp2():
    """Pytest / Test runner entrypoint."""
    results = evaluate_router_on_wp2(
        experiment_name="2-L-Laya-TopK",
        predictor=two_layer_laya_topk_predictor,
        description="Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 Top-K Tool RAG with LAYA (k=3)."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="2-L-Laya-TopK",
        predictor=two_layer_laya_topk_predictor,
        description="Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 Top-K Tool RAG with LAYA (k=3)."
    )
