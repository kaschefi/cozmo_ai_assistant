# backend/test/digital/routers/single_layer_laya_topk.py
"""
Router 5: Single-Layer LAYA Router with Top-K Tool Retrieval Evaluation (WP2 Experiment).

Implementation:
Uses a single-layer pipeline with Top-K Tool RAG filtering:
- No Layer 1 reflexes: queries are evaluated solely through the decision pipeline.
- FastEmbed FAISS Tool Vector Store retrieves only the top-k most semantically relevant
  candidate tools (default k=3) instead of passing all 15 tools at once.
- If no tools satisfy the distance threshold, immediately falls back to conversational "none".
- If candidate tools match, dynamically passes ONLY those top-k tools (plus "none") as
  typed choice criteria into the LAYA Typed Decision Model (`convaiinnovations/laya-typed-decisions`).

Running this file automatically executes the benchmark and adds the run to the
'WP2' experiment in the LangSmith dashboard.
"""

import os
import sys
import time
from typing import Dict, Any

# Ensure backend directory is in path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import laya
from core.routing.layer1.semantic_layer import initialize_router
from core.routing.layer2.tool_vector_db import tool_rag_registry
from test.digital.routers.tools_config import TOOLS_15, build_laya_questions
from test.digital.routers.harness import evaluate_router_on_wp2

# Singletons for fast repeated evaluation
_LAYA_AGENT = None
_LAYA_TOPK_INITIALIZED = False


def ensure_single_layer_laya_topk_ready(model_id: str = "convaiinnovations/laya-typed-decisions"):
    """Ensures Tool RAG vector index is built and LAYA model is loaded and warmed up."""
    global _LAYA_AGENT, _LAYA_TOPK_INITIALIZED
    if not _LAYA_TOPK_INITIALIZED:
        print(f"[SingleLayerLayaTopK] Initializing Tool RAG registry and LAYA model ({model_id})...")
        if tool_rag_registry.db is None:
            initialize_router()

        if _LAYA_AGENT is None:
            _LAYA_AGENT = laya.load(model_id)

        # Warmup pass with sample top-k criteria
        sample_tools = tool_rag_registry.search_relevant_tools("warmup", k=3)
        sample_dict = {t["name"]: t["description"] for t in sample_tools}
        sample_dict["none"] = TOOLS_15["none"]
        _ = _LAYA_AGENT.predict("warmup", build_laya_questions(sample_dict))

        _LAYA_TOPK_INITIALIZED = True
        print("[SingleLayerLayaTopK] Router ready.\n")
    return _LAYA_AGENT


def single_layer_laya_topk_predictor(inputs: dict, k: int = 3) -> dict:
    """
    Evaluates a user query through Single-Layer LAYA Router with Top-K Tool Retrieval.
    
    1. Retrieves top-k matching candidate tools from the FastEmbed Tool RAG index.
    2. If no candidate tools meet the similarity threshold, falls back to "none".
    3. Dynamically passes only the top-k candidates (+ "none") to the LAYA decision model.
    """
    agent = ensure_single_layer_laya_topk_ready()
    query = inputs["message"].strip()
    start_time = time.perf_counter()

    # Step 1: Query Tool Vector DB for top-k relevant tools
    matched_tools = tool_rag_registry.search_relevant_tools(query, k=k)

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
        "top_k_candidates": [t["name"] for t in matched_tools],
        "pipeline": f"Single-Layer (Top-{k} Tool RAG + LAYA)"
    }


class SingleLayerLayaTopKRouter:
    """Class wrapper around single_layer_laya_topk_predictor for backward compatibility."""
    def __init__(self, k: int = 3):
        self.k = k

    def route(self, query: str) -> dict:
        return single_layer_laya_topk_predictor({"message": query}, k=self.k)


def test_single_layer_laya_topk_router_wp2():
    """Pytest / Test runner entrypoint."""
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
