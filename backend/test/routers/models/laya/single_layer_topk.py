# backend/test/routers/models/laya/single_layer_topk.py
"""
Router: Single-Layer LAYA Router with Top-K Tool Retrieval Evaluation.

Implementation:
Uses a single-layer pipeline with Top-K Tool RAG filtering:
- No Layer 1 reflexes: queries are evaluated solely through the decision pipeline.
- FastEmbed FAISS Tool Vector Store retrieves only the top-k most semantically relevant
  candidate tools (default k=3) instead of passing all tools at once.
- If no tools satisfy the distance threshold, immediately falls back to conversational "none".
- If candidate tools match, dynamically passes ONLY those top-k tools (plus "none") as
  typed choice criteria into the LAYA Typed Decision Model (`convaiinnovations/laya-typed-decisions`).
"""

import os
import sys
import time
from typing import Dict, Any, Callable, Optional

# Ensure backend directory is in path (5 levels up from models/laya/)
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import laya
from test.routers.tools import (
    TOOLS_15,
    build_laya_questions,
    get_tools_preset,
    create_scoped_tool_rag_registry,
)
from test.routers.harness import evaluate_router_on_wp2, evaluate_router_on_benchmark

# Singletons for fast repeated evaluation
_LAYA_AGENT = None
_LAYA_TOPK_INITIALIZED = False
_WP2_LAYA_RAG = None
_SCOPED_RAG_CACHE: Dict[int, Any] = {}
_PREDICTOR_CACHE: Dict[tuple, Callable[[dict], dict]] = {}


def ensure_single_layer_laya_topk_ready(model_id: str = "convaiinnovations/laya-typed-decisions"):
    """Ensures dedicated WP2 Tool RAG index is built and LAYA model is loaded and warmed up."""
    global _LAYA_AGENT, _LAYA_TOPK_INITIALIZED, _WP2_LAYA_RAG
    if not _LAYA_TOPK_INITIALIZED:
        print(f"[SingleLayerLayaTopK] Initializing WP2 Tool RAG registry and LAYA model ({model_id})...")
        if _WP2_LAYA_RAG is None:
            _WP2_LAYA_RAG = create_scoped_tool_rag_registry(TOOLS_15)

        if _LAYA_AGENT is None:
            _LAYA_AGENT = laya.load(model_id)

        # Warmup pass with sample top-k criteria
        sample_tools = _WP2_LAYA_RAG.search_relevant_tools("warmup", k=3)
        sample_dict = {t["name"]: t["description"] for t in sample_tools}
        sample_dict["none"] = TOOLS_15["none"]
        _ = _LAYA_AGENT.predict("warmup", build_laya_questions(sample_dict))

        _LAYA_TOPK_INITIALIZED = True
        print("[SingleLayerLayaTopK] Router ready.\n")
    return _LAYA_AGENT


def single_layer_laya_topk_predictor(inputs: dict, k: int = 3) -> dict:
    """
    Evaluates a user query through Single-Layer LAYA Router with Top-K Tool Retrieval (15 tools default).
    """
    agent = ensure_single_layer_laya_topk_ready()
    query = inputs["message"].strip()
    start_time = time.perf_counter()

    # Step 1: Query dedicated WP2 Tool Vector DB for top-k relevant tools
    matched_tools = _WP2_LAYA_RAG.search_relevant_tools(query, k=k)

    # Step 2: If no tools passed similarity threshold, bypass LAYA and return "none"
    if not matched_tools:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": "none",
            "confidence": 1.0,
            "latency_ms": latency_ms,
            "probabilities": {"none": 1.0},
            "top_k_candidates": [],
            "pipeline": f"Single-Layer (Top-{k} Tool RAG + LAYA)"
        }

    # Step 3: Dynamically construct choice criteria for ONLY the retrieved top-k tools + "none"
    tools_dict = {tool["name"]: tool["description"] for tool in matched_tools}
    tools_dict["none"] = TOOLS_15["none"]
    questions = build_laya_questions(tools_dict)

    # Step 4: Evaluate focused candidates with LAYA
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
        "top_k_candidates": [tool["name"] for tool in matched_tools],
        "pipeline": f"Single-Layer (Top-{k} Tool RAG + LAYA)"
    }


def get_single_layer_laya_topk_predictor(
    num_tools: int = 20,
    k: int = 3,
    model_id: str = "convaiinnovations/laya-typed-decisions"
) -> Callable[[dict], dict]:
    """
    Returns a configured predictor callable for N tools (20, 30, 50, 100)
    with Top-K Tool RAG filtering + LAYA decision model.
    """
    global _PREDICTOR_CACHE
    cache_key = (num_tools, k)
    if cache_key in _PREDICTOR_CACHE:
        return _PREDICTOR_CACHE[cache_key]

    agent = ensure_single_layer_laya_topk_ready(model_id=model_id)
    tools_dict = get_tools_preset(num_tools)

    if num_tools not in _SCOPED_RAG_CACHE:
        print(f"[SingleLayerLayaTopK] Building dedicated FAISS Tool RAG index for {num_tools} tools...")
        _SCOPED_RAG_CACHE[num_tools] = create_scoped_tool_rag_registry(tools_dict)
    local_rag = _SCOPED_RAG_CACHE[num_tools]

    def scaled_predictor(inputs: dict) -> dict:
        query = inputs["message"].strip()
        start_time = time.perf_counter()

        # Step 1: Query dedicated Tool Vector DB containing ONLY this experiment's tools
        matched_tools = local_rag.search_relevant_tools(query, k=k)

        if not matched_tools:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "route": "none",
                "confidence": 1.0,
                "latency_ms": latency_ms,
                "probabilities": {"none": 1.0},
                "top_k_candidates": [],
                "pipeline": f"Single-Layer (Top-{k} Tool RAG + LAYA - {num_tools} Tools)"
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
            "confidence": confidence,
            "latency_ms": latency_ms,
            "probabilities": decision.get("probabilities", {}),
            "top_k_candidates": [tool["name"] for tool in matched_tools],
            "pipeline": f"Single-Layer (Top-{k} Tool RAG + LAYA - {num_tools} Tools)"
        }

    _PREDICTOR_CACHE[cache_key] = scaled_predictor
    return scaled_predictor


class SingleLayerLayaTopKRouter:
    """Class wrapper around single_layer_laya_topk_predictor for backward compatibility."""
    def __init__(self, num_tools: int = 20, k: int = 3):
        self._predictor = get_single_layer_laya_topk_predictor(num_tools, k=k)

    def route(self, query: str) -> dict:
        return self._predictor({"message": query})


def test_single_layer_laya_topk_router_wp2():
    """Pytest / Test runner entrypoint for WP2."""
    results = evaluate_router_on_wp2(
        experiment_name="1-L-Laya-TopK",
        predictor=single_layer_laya_topk_predictor,
        description="Single-Layer LAYA router with Top-K FastEmbed Tool RAG retrieval (k=3)."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="1-L-Laya-TopK",
        predictor=single_layer_laya_topk_predictor,
        description="Single-Layer LAYA router with Top-K FastEmbed Tool RAG retrieval (k=3)."
    )
