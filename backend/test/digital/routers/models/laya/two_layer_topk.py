# backend/test/digital/routers/models/laya/two_layer_topk.py
"""
Router: Two-Layer Architecture with Top-K LAYA Router Evaluation.

Implementation:
Uses the two-layer intelligence pipeline combining fast reflexes with Top-K LAYA:
- Layer 1: Fast deterministic FastEmbed semantic reflexes (~6ms) for physical & system reflex commands.
  If an utterance matches a reflex threshold, routes instantly without invoking Layer 2.
- Layer 2: FastEmbed FAISS Tool Vector Store retrieves only the top-k most semantically relevant
  candidate tools (default k=3).
  - If no tools pass the similarity threshold, falls back to conversational "none".
  - If candidate tools match, dynamically passes ONLY those top-k tools (plus "none") as
    typed choice criteria into the LAYA Typed Decision Model (`convaiinnovations/laya-typed-decisions`).
"""

import os
import sys
import time
from typing import Dict, Any, Callable, Optional

# Ensure backend directory is in path (5 levels up from models/laya/)
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import laya
from core.routing.layer1.semantic_layer import check_layer_1
from core.routing.layer2.tool_vector_db import tool_rag_registry
from test.digital.routers.tools import (
    TOOLS_15,
    build_laya_questions,
    get_tools_preset,
    register_all_tools_to_rag,
    TOOL_RAG_REGISTRY_SPECS
)
from test.digital.routers.harness import evaluate_router_on_wp2, evaluate_router_on_benchmark

# Singletons for fast repeated evaluation
_LAYA_AGENT = None
_TWO_LAYER_TOPK_INITIALIZED = False
_PREDICTOR_CACHE: Dict[tuple, Callable[[dict], dict]] = {}


def ensure_two_layer_laya_topk_ready(model_id: str = "convaiinnovations/laya-typed-decisions"):
    """Initializes Layer 1 semantic reflexes, Layer 2 Tool RAG index, and LAYA decision model."""
    global _LAYA_AGENT, _TWO_LAYER_TOPK_INITIALIZED
    if not _TWO_LAYER_TOPK_INITIALIZED:
        print(f"[TwoLayerLayaTopK] Initializing Layer 1 Reflexes and Layer 2 Top-K LAYA ({model_id})...")
        _ = check_layer_1("warmup")
        register_all_tools_to_rag(specs=TOOL_RAG_REGISTRY_SPECS)
        tool_rag_registry.build_index()

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
    Evaluates a user query through Two-Layer Router with Top-K LAYA (15 tools default).
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

    candidate_dict = {tool["name"]: tool["description"] for tool in matched_tools}
    candidate_dict["none"] = TOOLS_15["none"]
    questions = build_laya_questions(candidate_dict)

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
        "top_k_candidates": [tool["name"] for tool in matched_tools],
        "pipeline": f"Two-Layer (Tier 2 Top-{k} Tool RAG + LAYA)"
    }


def get_two_layer_laya_topk_predictor(
    num_tools: int = 20,
    k: int = 3,
    model_id: str = "convaiinnovations/laya-typed-decisions"
) -> Callable[[dict], dict]:
    """
    Returns a configured predictor callable for N tools (20, 30, 50, 100)
    combining Layer 1 reflexes with Layer 2 Top-K FastEmbed retrieval + LAYA.
    """
    global _PREDICTOR_CACHE
    cache_key = (num_tools, k)
    if cache_key in _PREDICTOR_CACHE:
        return _PREDICTOR_CACHE[cache_key]

    agent = ensure_two_layer_laya_topk_ready(model_id=model_id)
    tools_dict = get_tools_preset(num_tools)

    def scaled_predictor(inputs: dict) -> dict:
        query = inputs["message"].strip()
        start_time = time.perf_counter()

        # Step 1: Check Layer 1 Semantic Reflexes
        layer_1_route = check_layer_1(query)
        if layer_1_route and (layer_1_route in tools_dict or layer_1_route == "none"):
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "route": layer_1_route,
                "tier": "Tier 1 (Semantic Reflex)",
                "latency_ms": latency_ms,
                "pipeline": "Two-Layer (Tier 1 FastEmbed Reflex)"
            }

        # Step 2: Fall back to Layer 2 Tool RAG + LAYA Decision Model
        matched_tools = tool_rag_registry.search_relevant_tools(query, k=k)
        matched_tools = [t for t in matched_tools if t["name"] in tools_dict]

        if not matched_tools:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "route": "none",
                "tier": "Tier 2 (Tool RAG + LAYA)",
                "confidence": 1.0,
                "latency_ms": latency_ms,
                "probabilities": {"none": 1.0},
                "top_k_candidates": [],
                "pipeline": f"Two-Layer (Tier 2 Top-{k} Tool RAG + LAYA - {num_tools} Tools)"
            }

        candidate_dict = {tool["name"]: tool["description"] for tool in matched_tools}
        candidate_dict["none"] = tools_dict["none"]
        questions = build_laya_questions(candidate_dict)

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
            "top_k_candidates": [tool["name"] for tool in matched_tools],
            "pipeline": f"Two-Layer (Tier 2 Top-{k} Tool RAG + LAYA - {num_tools} Tools)"
        }

    _PREDICTOR_CACHE[cache_key] = scaled_predictor
    return scaled_predictor


class TwoLayerLayaTopKRouter:
    """Class wrapper around two_layer_laya_topk_predictor for backward compatibility."""
    def __init__(self, num_tools: int = 20, k: int = 3):
        self._predictor = get_two_layer_laya_topk_predictor(num_tools, k=k)

    def route(self, query: str) -> dict:
        return self._predictor({"message": query})


def test_two_layer_laya_topk_router_wp2():
    """Pytest / Test runner entrypoint for WP2."""
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
