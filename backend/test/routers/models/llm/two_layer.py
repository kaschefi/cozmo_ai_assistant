# backend/test/routers/models/llm/two_layer.py
"""
Router: Two-Layer Architecture with LLM Router Evaluation.

Implementation:
Uses the two-layer intelligence pipeline:
- Layer 1: Fast deterministic FastEmbed semantic reflexes (~6ms) for physical & desktop commands (0 tokens).
- Layer 2: FastEmbed FAISS Tool RAG retrieves top-k candidates (default k=3), then invokes the LLM
  (qwen2.5:3b or configured provider) with ONLY those top-k tools in a compact structured prompt.
  Generates input and output tokens tracked directly in LangSmith.
"""

import os
import sys
import time
from typing import Dict, Any, Callable, Optional, List
from langchain_core.messages import SystemMessage, HumanMessage

# Ensure backend directory is in path (5 levels up from models/llm/)
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from core.routing.llm_factory import get_llm
from core.routing.baseline.baseline_router import BaselineDecision
from core.routing.layer1.semantic_layer import check_layer_1
from core.routing.layer2.tool_vector_db import tool_rag_registry
from test.routers.tools import (
    TOOLS_15,
    get_tools_preset,
    register_all_tools_to_rag,
    TOOL_RAG_REGISTRY_SPECS
)
from test.routers.harness import evaluate_router_on_wp2, evaluate_router_on_benchmark

_TWO_LAYER_LLM_INITIALIZED = False
_PREDICTOR_CACHE: Dict[int, Callable[[dict], dict]] = {}


def _build_two_layer_llm_prompt(candidate_tools: List[Dict[str, str]]) -> str:
    """Builds a compact prompt containing ONLY the top-k retrieved tools."""
    tool_menu_string = ""
    for tool in candidate_tools:
        tool_menu_string += f'- "{tool["name"]}": {tool["description"]}\n'

    return f"""You are Cozmo's routing supervisor. Your role is to accurately classify the intent of the user's latest message.

AVAILABLE UTILITY CHANNELS RETRIEVED FOR THIS TURN:
{tool_menu_string}- "none": Core conversational channel. Fall back to this for anything that doesn't strictly match a specific tool option above.

CLASSIFICATION RULES:
1. INTENT-DRIVEN SELECTION: You must ONLY select a specific tool if the user is explicitly requesting an action or service matching one of the retrieved options above.
2. CASUAL CHAT & PERSONAL FACTS ("none"): If the user is sharing personal information, greeting, chatting casually, or if no retrieved tool matches, select "none".
3. STRICT FORMAT: Return a structured decision containing the exact string name of the chosen route.
4. DO NOT FULFILL THE REQUEST: Your only job is classification.
"""


def ensure_two_layer_llm_ready():
    """Initializes Layer 1 reflexes and Layer 2 FAISS Tool RAG index."""
    global _TWO_LAYER_LLM_INITIALIZED
    if not _TWO_LAYER_LLM_INITIALIZED:
        print("[TwoLayerLLM] Initializing FastEmbed reflexes and Tool RAG registry...")
        _ = check_layer_1("warmup")
        register_all_tools_to_rag(specs=TOOL_RAG_REGISTRY_SPECS)
        tool_rag_registry.build_index()
        _TWO_LAYER_LLM_INITIALIZED = True
        print("[TwoLayerLLM] Two-Layer LLM pipeline ready.\n")


def two_layer_llm_predictor(inputs: dict, k: int = 3) -> dict:
    """
    Evaluates a user query through Production Two-Layer LLM Router (WP2 15 tools default).
    Reflexes handle physical actions (0 tokens); Layer 2 retrieves top-k tools and invokes the LLM.
    """
    ensure_two_layer_llm_ready()
    query = inputs["message"].strip()
    start_time = time.perf_counter()

    # Step 1: Check Layer 1 Semantic Reflexes (~6ms, 0 LLM tokens)
    layer_1_route = check_layer_1(query)
    if layer_1_route and (layer_1_route in TOOLS_15 or layer_1_route == "none"):
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": layer_1_route,
            "tier": "Tier 1 (Semantic Reflex)",
            "latency_ms": latency_ms,
            "pipeline": "Two-Layer (Tier 1 FastEmbed Reflex - 0 Tokens)"
        }

    # Step 2: Retrieve Top-K tools from Tool RAG
    matched_tools = tool_rag_registry.search_relevant_tools(query, k=k)
    matched_tools = [t for t in matched_tools if t["name"] in TOOLS_15]

    if not matched_tools:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": "none",
            "tier": "Tier 2 (Tool RAG Filtered)",
            "confidence": 1.0,
            "latency_ms": latency_ms,
            "top_k_candidates": [],
            "pipeline": "Two-Layer (Tier 2 RAG - 0 Tokens)"
        }

    # Step 3: Invoke LLM with only the retrieved candidate tools (generates tokens)
    router_llm = get_llm("ROUTER_LLM_MODEL", "qwen2.5:3b", temperature=0.0)
    structured_router = router_llm.with_structured_output(BaselineDecision)

    system_prompt = _build_two_layer_llm_prompt(matched_tools)
    try:
        decision = structured_router.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ])
        candidate_names = {t["name"] for t in matched_tools}
        route = decision.route if (decision.route in candidate_names or decision.route == "none") else "none"
        reasoning = decision.reasoning or ""
    except Exception as e:
        route = "none"
        reasoning = f"LLM inference error: {str(e)}"

    latency_ms = (time.perf_counter() - start_time) * 1000
    return {
        "route": route,
        "reasoning": reasoning,
        "tier": "Tier 2 (Tool RAG + LLM)",
        "latency_ms": latency_ms,
        "top_k_candidates": [t["name"] for t in matched_tools],
        "pipeline": "Two-Layer (Tier 2 LLM)"
    }


def get_two_layer_llm_predictor(
    num_tools: int = 20,
    k: int = 3,
    model_env_var: str = "ROUTER_LLM_MODEL",
    default_model: str = "qwen2.5:3b",
    temperature: float = 0.0
) -> Callable[[dict], dict]:
    """
    Returns a configured predictor callable for N tools (20, 30, 50, 100)
    combining Layer 1 reflexes (0 tokens) with Layer 2 Top-K Tool RAG + LLM Structured Output.
    """
    global _PREDICTOR_CACHE
    if num_tools in _PREDICTOR_CACHE:
        return _PREDICTOR_CACHE[num_tools]

    ensure_two_layer_llm_ready()
    tools_dict = get_tools_preset(num_tools)

    router_llm = get_llm(model_env_var, default_model, temperature=temperature)
    structured_router = router_llm.with_structured_output(BaselineDecision, include_raw=True)

    def scaled_predictor(inputs: dict) -> dict:
        query = inputs["message"].strip()
        if not query:
            return {"route": "none", "reasoning": "Empty input", "latency_ms": 0.0, "tokens_used": 0, "pipeline": f"Two-Layer (Tier 2 LLM - {num_tools} Tools)"}

        start_time = time.perf_counter()

        # Step 1: Check Layer 1 Semantic Reflexes (0 LLM tokens, ~6ms)
        layer_1_route = check_layer_1(query)
        if layer_1_route and (layer_1_route in tools_dict or layer_1_route == "none"):
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "route": layer_1_route,
                "tier": "Tier 1 (Semantic Reflex)",
                "latency_ms": latency_ms,
                "tokens_used": 0,
                "total_tokens": 0,
                "pipeline": "Two-Layer (Tier 1 FastEmbed Reflex - 0 Tokens)"
            }

        # Step 2: Query Tool Vector DB for top-k relevant tools
        matched_tools = tool_rag_registry.search_relevant_tools(query, k=k)
        matched_tools = [t for t in matched_tools if t["name"] in tools_dict]

        if not matched_tools:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "route": "none",
                "tier": "Tier 2 (Tool RAG Filtered)",
                "confidence": 1.0,
                "latency_ms": latency_ms,
                "probabilities": {"none": 1.0},
                "top_k_candidates": [],
                "tokens_used": 0,
                "total_tokens": 0,
                "pipeline": f"Two-Layer (Tier 2 RAG - 0 Tokens - {num_tools} Tools)"
            }

        # Step 3: Invoke LLM with ONLY the Top-K retrieved tools (Generates Input/Output Tokens)
        system_prompt = _build_two_layer_llm_prompt(matched_tools)
        tokens_used = 0
        try:
            res = structured_router.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ])
            decision = res.get("parsed") if isinstance(res, dict) else res
            raw_msg = res.get("raw") if isinstance(res, dict) else None
            if raw_msg and hasattr(raw_msg, "usage_metadata") and raw_msg.usage_metadata:
                tokens_used = raw_msg.usage_metadata.get("total_tokens", 0)
            elif raw_msg and hasattr(raw_msg, "response_metadata"):
                prompt_tokens = raw_msg.response_metadata.get("prompt_eval_count", 0)
                eval_tokens = raw_msg.response_metadata.get("eval_count", 0)
                tokens_used = prompt_tokens + eval_tokens

            candidate_names = {t["name"] for t in matched_tools}
            if decision and hasattr(decision, "route"):
                route = decision.route if (decision.route in candidate_names or decision.route == "none") else "none"
                reasoning = decision.reasoning or ""
            else:
                route = "none"
                reasoning = "Could not parse structured decision"
        except Exception as e:
            route = "none"
            reasoning = f"LLM error: {str(e)}"

        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": route,
            "reasoning": reasoning,
            "tier": "Tier 2 (Tool RAG + LLM)",
            "latency_ms": latency_ms,
            "top_k_candidates": [t["name"] for t in matched_tools],
            "tokens_used": tokens_used,
            "total_tokens": tokens_used,
            "pipeline": f"Two-Layer (Tier 2 LLM - {num_tools} Tools)"
        }

    _PREDICTOR_CACHE[num_tools] = scaled_predictor
    return scaled_predictor


def test_two_layer_llm_router_wp2():
    """Pytest / Test runner entrypoint."""
    results = evaluate_router_on_wp2(
        experiment_name="2-L-LLM",
        predictor=two_layer_llm_predictor,
        description="Production Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 Tool RAG with Ollama (qwen2.5:3b)."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="2-Layer-LLM",
        predictor=two_layer_llm_predictor,
        description="Production Two-Layer Router: Layer 1 FastEmbed Reflexes + Layer 2 Tool RAG with Ollama (qwen2.5:3b)."
    )
