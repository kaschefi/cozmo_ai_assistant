# backend/test/routers/models/laya/two_layer_topk.py
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
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import laya
from core.routing.layer1.semantic_layer import check_layer_1
from test.routers.tools import (
    TOOLS_15,
    build_laya_questions,
    get_tools_preset,
    create_scoped_tool_rag_registry,
    TOOL_TO_DOMAIN,
)
from test.routers.harness import evaluate_router_on_wp2, evaluate_router_on_benchmark

# Singletons for fast repeated evaluation
_LAYA_AGENT = None
_TWO_LAYER_TOPK_INITIALIZED = False
_WP2_LAYA_RAG = None
_SCOPED_RAG_CACHE: Dict[int, Any] = {}
_PREDICTOR_CACHE: Dict[tuple, Callable[[dict], dict]] = {}


def ensure_two_layer_laya_topk_ready(model_id: str = "convaiinnovations/laya-typed-decisions"):
    """Initializes Layer 1 semantic reflexes, dedicated WP2 Tool RAG index, and LAYA decision model."""
    global _LAYA_AGENT, _TWO_LAYER_TOPK_INITIALIZED, _WP2_LAYA_RAG
    if not _TWO_LAYER_TOPK_INITIALIZED:
        print(f"[TwoLayerLayaTopK] Initializing Layer 1 Reflexes and WP2 Top-K LAYA ({model_id})...")
        _ = check_layer_1("warmup")
        if _WP2_LAYA_RAG is None:
            _WP2_LAYA_RAG = create_scoped_tool_rag_registry(TOOLS_15)

        if _LAYA_AGENT is None:
            _LAYA_AGENT = laya.load(model_id)

        # Warmup pass with sample top-k criteria
        sample_tools = _WP2_LAYA_RAG.search_relevant_tools("warmup", k=3)
        sample_dict = {t["name"]: t["description"] for t in sample_tools}
        sample_dict["none"] = TOOLS_15["none"]
        _ = _LAYA_AGENT.predict("warmup", build_laya_questions(sample_dict))

        _TWO_LAYER_TOPK_INITIALIZED = True
        print("[TwoLayerLayaTopK] Router ready.\n")
    return _LAYA_AGENT


def validate_layer_1_reflex(layer_1_route: Optional[str], query: str) -> Optional[str]:
    """
    Guards Layer 1 FastEmbed reflexes against cross-namespace false triggers:
    1. Prevents robot docking reflexes from stealing desktop OS power commands (laptop/PC sleep).
    2. Prevents robot panoramic arc sweeps from stealing vertical head tilts (look up/down).
    3. Prevents chassis kinematic movement from stealing smart home lighting/climate commands.
    4. Prevents clock time/date reflexes from stealing calendar appointments or countdown timers.
    """
    if not layer_1_route:
        return None

    query_lower = query.lower()
    q_words = set(query_lower.split())

    # Guard 1: dock_with_charger vs desktop OS sleep
    if layer_1_route == "dock_with_charger":
        desktop_cues = {"laptop", "pc", "computer", "mac", "desktop", "windows", "monitor", "screen", "suspend", "hibernate"}
        if q_words & desktop_cues:
            return None

    # Guard 2: arc_sweep vs vertical head tilt
    if layer_1_route == "arc_sweep":
        vertical_cues = {"up", "upward", "upwards", "down", "downward", "downwards", "ceiling", "desk", "floor", "tracks"}
        if q_words & vertical_cues:
            return None

    # Guard 3: Physical chassis kinematics vs Smart Home
    if layer_1_route in {"move_forward", "move_backward", "turn_left", "turn_right", "turn_around", "stop_movement"}:
        smart_home_cues = {"light", "lights", "lamp", "hue", "dim", "brightness", "color", "colour", "plug", "socket", "thermostat", "temperature"}
        if q_words & smart_home_cues:
            return None

    # Guard 4: tell_time / get_date vs alarms & calendar
    if layer_1_route in {"tell_time", "get_date"}:
        time_event_cues = {"timer", "countdown", "alarm", "standup", "meeting", "sync", "schedule", "reschedule", "appointment", "pomodoro"}
        if q_words & time_event_cues:
            return None

    return layer_1_route


def two_layer_laya_topk_predictor(inputs: dict, k: int = 5, head_max_len: int = 384) -> dict:
    """
    Evaluates a user query through Two-Layer Router with Top-K LAYA (15 tools default).
    """
    agent = ensure_two_layer_laya_topk_ready()
    query = inputs["message"].strip()
    start_time = time.perf_counter()

    # Step 1: Check Layer 1 Semantic Reflexes (~6ms deterministic match)
    layer_1_route = validate_layer_1_reflex(check_layer_1(query), query)
    if layer_1_route:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": layer_1_route,
            "tier": "Tier 1 (Semantic Reflex)",
            "latency_ms": latency_ms,
            "pipeline": "Two-Layer (Tier 1 FastEmbed Reflex)"
        }

    # Step 2: Fall back to Layer 2 Tool RAG + Hierarchical Domain Selection + LAYA
    probe_k = max(k * 2, 8)
    matched_tools = _WP2_LAYA_RAG.search_relevant_tools(query, k=probe_k, distance_threshold=1.15)

    if not matched_tools or (matched_tools and matched_tools[0].get("score", 0.0) > 1.10):
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

    top_score = matched_tools[0].get("score", 0.0)
    top_tool = matched_tools[0]["name"]
    primary_domain = TOOL_TO_DOMAIN.get(top_tool)

    # Hierarchical Domain Selection (pruning cross-namespace lexical distractors):
    top3_domains = [TOOL_TO_DOMAIN.get(m["name"]) for m in matched_tools[:3]]
    if top_score <= 0.60 or top3_domains.count(primary_domain) >= 2:
        allowed_domains = {primary_domain}
    else:
        allowed_domains = {primary_domain}
        for m in matched_tools[1:4]:
            if m.get("score", 0.0) <= top_score + 0.12:
                d = TOOL_TO_DOMAIN.get(m["name"])
                if d:
                    allowed_domains.add(d)

    active_tools = [
        t for t in matched_tools
        if (TOOL_TO_DOMAIN.get(t["name"]) in allowed_domains or not allowed_domains)
        and t.get("score", 0.0) <= top_score + 0.16
    ]
    if not active_tools:
        active_tools = [matched_tools[0]]

    active_tools = active_tools[:4]

    candidate_dict = {tool["name"]: tool["description"] for tool in active_tools}
    candidate_dict["none"] = TOOLS_15["none"]
    questions = build_laya_questions(candidate_dict)

    result = agent.predict(query, questions, head_max_len=head_max_len)
    answers = result.get("answers", result)
    decision = answers.get("tool_selection", {})

    selected_route = decision.get("choice", "none")
    confidence = decision.get("confidence", 0.0)

    # Confidence Gating for "none":
    # If "none" is chosen with low confidence (< 0.12) but FAISS retrieved an extremely strong
    # domain match (top_score <= 0.65), override "none" with the highest-probability tool candidate.
    if selected_route == "none" and confidence < 0.12 and top_score <= 0.65:
        probs = decision.get("probabilities", {})
        tool_probs = {k: v for k, v in probs.items() if k != "none"}
        if tool_probs:
            best_tool = max(tool_probs, key=tool_probs.get)
            if tool_probs[best_tool] >= 0.25:
                selected_route = best_tool

    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "route": selected_route,
        "tier": "Tier 2 (Tool RAG + LAYA)",
        "confidence": confidence,
        "latency_ms": latency_ms,
        "probabilities": decision.get("probabilities", {}),
        "top_k_candidates": [tool["name"] for tool in active_tools],
        "pipeline": f"Two-Layer (Tier 2 Top-{k} Tool RAG + LAYA)"
    }


def get_two_layer_laya_topk_predictor(
    num_tools: int = 20,
    k: int = 5,
    model_id: str = "convaiinnovations/laya-typed-decisions",
    head_max_len: int = 384
) -> Callable[[dict], dict]:
    """
    Returns a configured predictor callable for N tools (20, 30, 50, 100)
    combining Layer 1 reflexes with Layer 2 Top-K FastEmbed retrieval + LAYA.
    """
    global _PREDICTOR_CACHE
    cache_key = (num_tools, k, head_max_len)
    if cache_key in _PREDICTOR_CACHE:
        return _PREDICTOR_CACHE[cache_key]

    agent = ensure_two_layer_laya_topk_ready(model_id=model_id)
    tools_dict = get_tools_preset(num_tools)

    if num_tools not in _SCOPED_RAG_CACHE:
        print(f"[TwoLayerLayaTopK] Building dedicated FAISS Tool RAG index for {num_tools} tools...")
        _SCOPED_RAG_CACHE[num_tools] = create_scoped_tool_rag_registry(tools_dict)
    local_rag = _SCOPED_RAG_CACHE[num_tools]

    def scaled_predictor(inputs: dict) -> dict:
        query = inputs["message"].strip()
        start_time = time.perf_counter()

        # Step 1: Check Layer 1 Semantic Reflexes
        layer_1_route = validate_layer_1_reflex(check_layer_1(query), query)
        if layer_1_route and (layer_1_route in tools_dict or layer_1_route == "none"):
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "route": layer_1_route,
                "tier": "Tier 1 (Semantic Reflex)",
                "latency_ms": latency_ms,
                "pipeline": "Two-Layer (Tier 1 FastEmbed Reflex)"
            }

        # Step 2: Fall back to Layer 2 Tool RAG + Hierarchical Domain Selection + LAYA
        probe_k = max(k * 2, 8)
        matched_tools = local_rag.search_relevant_tools(query, k=probe_k, distance_threshold=1.15)

        if not matched_tools or (matched_tools and matched_tools[0].get("score", 0.0) > 1.10):
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

        top_score = matched_tools[0].get("score", 0.0)
        top_tool = matched_tools[0]["name"]
        primary_domain = TOOL_TO_DOMAIN.get(top_tool)

        # Hierarchical Domain Selection (pruning cross-namespace lexical distractors):
        top3_domains = [TOOL_TO_DOMAIN.get(m["name"]) for m in matched_tools[:3]]
        if top_score <= 0.60 or top3_domains.count(primary_domain) >= 2:
            allowed_domains = {primary_domain}
        else:
            allowed_domains = {primary_domain}
            for m in matched_tools[1:4]:
                if m.get("score", 0.0) <= top_score + 0.12:
                    d = TOOL_TO_DOMAIN.get(m["name"])
                    if d:
                        allowed_domains.add(d)

        # Retain candidate tools from allowed domains within distance delta
        active_tools = [
            t for t in matched_tools
            if (TOOL_TO_DOMAIN.get(t["name"]) in allowed_domains or not allowed_domains)
            and t.get("score", 0.0) <= top_score + 0.16
        ]
        if not active_tools:
            active_tools = [matched_tools[0]]

        # Bound candidates to at most 4 tools to prevent ModernBERT softmax logit collapse
        active_tools = active_tools[:4]

        candidate_dict = {tool["name"]: tool["description"] for tool in active_tools}
        candidate_dict["none"] = tools_dict["none"]
        questions = build_laya_questions(candidate_dict)

        result = agent.predict(query, questions, head_max_len=head_max_len)
        answers = result.get("answers", result)
        decision = answers.get("tool_selection", {})

        selected_route = decision.get("choice", "none")
        confidence = decision.get("confidence", 0.0)

        # Confidence Gating for "none":
        # If "none" is chosen with low confidence (< 0.12) but FAISS retrieved an extremely strong
        # domain match (top_score <= 0.65), override "none" with the highest-probability tool candidate.
        if selected_route == "none" and confidence < 0.12 and top_score <= 0.65:
            probs = decision.get("probabilities", {})
            tool_probs = {k: v for k, v in probs.items() if k != "none"}
            if tool_probs:
                best_tool = max(tool_probs, key=tool_probs.get)
                if tool_probs[best_tool] >= 0.25:
                    selected_route = best_tool

        latency_ms = (time.perf_counter() - start_time) * 1000

        return {
            "route": selected_route,
            "tier": "Tier 2 (Tool RAG + LAYA)",
            "confidence": confidence,
            "latency_ms": latency_ms,
            "probabilities": decision.get("probabilities", {}),
            "top_k_candidates": [tool["name"] for tool in active_tools],
            "pipeline": f"Two-Layer (Tier 2 Top-{k} Tool RAG + LAYA - {num_tools} Tools)"
        }

    _PREDICTOR_CACHE[cache_key] = scaled_predictor
    return scaled_predictor


class TwoLayerLayaTopKRouter:
    """Class wrapper around two_layer_laya_topk_predictor for backward compatibility."""
    def __init__(self, num_tools: int = 20, k: int = 5, head_max_len: int = 384):
        self._predictor = get_two_layer_laya_topk_predictor(num_tools, k=k, head_max_len=head_max_len)

    def route(self, query: str) -> dict:
        return self._predictor({"message": query})

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
