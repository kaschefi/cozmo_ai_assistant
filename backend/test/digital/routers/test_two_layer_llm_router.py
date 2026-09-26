# backend/test/digital/routers/test_two_layer_llm_router.py
"""
Router 2: Two-Layer Architecture with LLM Router Evaluation (WP2 Experiment).

Implementation:
Uses the existing production two-layer architecture:
- Layer 1: Fast deterministic FastEmbed semantic reflexes (~6ms) for physical & laptop commands.
- Layer 2: LangGraph Tool RAG Vector Store + Router Supervisor LLM (qwen2.5:3b).

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

from langchain_core.messages import HumanMessage
from core.routing.layer1.semantic_layer import check_layer_1
from core.routing.layer2.graph_nodes import tool_retrieval_node, route_query
from test.digital.routers.harness import evaluate_router_on_wp2


_TWO_LAYER_LLM_INITIALIZED = False


def ensure_two_layer_llm_warm():
    global _TWO_LAYER_LLM_INITIALIZED
    if not _TWO_LAYER_LLM_INITIALIZED:
        print("[TwoLayerLLM] Warming up FastEmbed and Ollama LLM...")
        _ = check_layer_1("warmup")
        state_input = {"messages": [HumanMessage(content="warmup")]}
        retrieval_output = tool_retrieval_node(state_input)
        _ = route_query({**state_input, **retrieval_output})
        _TWO_LAYER_LLM_INITIALIZED = True
        print("[TwoLayerLLM] Warmup complete.\n")


def two_layer_llm_predictor(inputs: dict) -> dict:
    """
    Evaluates a user query through the Production Two-Layer Router (Reflex + LLM RAG).
    """
    ensure_two_layer_llm_warm()
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

    # Step 2: Fall back to Layer 2 Tool RAG + Ollama LLM Classifier
    state_input = {"messages": [HumanMessage(content=query)]}
    retrieval_output = tool_retrieval_node(state_input)
    state_with_tools = {**state_input, **retrieval_output}
    decision = route_query(state_with_tools)
    layer_2_route = decision.get("next_route", "none")

    latency_ms = (time.perf_counter() - start_time) * 1000
    return {
        "route": layer_2_route,
        "tier": "Tier 2 (Tool RAG + LLM)",
        "latency_ms": latency_ms,
        "pipeline": "Two-Layer (Tier 2 Ollama Qwen2.5:3b)"
    }


def test_two_layer_llm_router_wp2():
    """Pytest / Test runner entrypoint."""
    results = evaluate_router_on_wp2(
        experiment_name="WP2-Two-Layer-LLM",
        predictor=two_layer_llm_predictor,
        description="Production Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 Tool RAG with Ollama (qwen2.5:3b)."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="WP2-Two-Layer-LLM",
        predictor=two_layer_llm_predictor,
        description="Production Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 Tool RAG with Ollama (qwen2.5:3b)."
    )
