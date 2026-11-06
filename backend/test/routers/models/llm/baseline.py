# backend/test/routers/models/llm/baseline.py
"""
Router: Baseline Monolithic LLM Router Evaluation.

Implementation:
Uses a monolithic single-shot baseline LLM router.
All N system tools and full descriptions are passed directly to the LLM (qwen2.5:3b or configured provider)
in a single prompt without Layer 1 reflexes or vector RAG.
"""

import os
import sys
import time
from typing import Dict, Any, Callable, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

# Ensure backend directory is in path (5 levels up from models/llm/)
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from core.routing.llm_factory import get_llm
from core.routing.baseline import baseline_classify_intent, BaselineDecision
from test.routers.tools import get_tools_preset
from test.routers.harness import evaluate_router_on_wp2, evaluate_router_on_benchmark

_BASELINE_INITIALIZED = False
_PREDICTOR_CACHE: Dict[int, Callable[[dict], dict]] = {}


def ensure_baseline_warm():
    global _BASELINE_INITIALIZED
    if not _BASELINE_INITIALIZED:
        print("[BaselineLLM] Warming up Ollama LLM...")
        try:
            _ = baseline_classify_intent("warmup")
        except Exception as e:
            print(f"[BaselineLLM] Warmup note: {e}")
        _BASELINE_INITIALIZED = True
        print("[BaselineLLM] Warmup complete.\n")


def baseline_router_predictor(inputs: dict) -> dict:
    """
    Evaluates a user query through the Baseline Monolithic LLM Router (WP2 15 tools).
    """
    ensure_baseline_warm()
    query = inputs["message"].strip()
    start_time = time.perf_counter()

    decision = baseline_classify_intent(query)
    latency_ms = (time.perf_counter() - start_time) * 1000

    return {
        "route": decision.route,
        "reasoning": decision.reasoning or "",
        "latency_ms": latency_ms,
        "pipeline": "Baseline (Monolithic All-Tools LLM)"
    }


def get_baseline_router_predictor(
    num_tools: int = 20,
    model_env_var: str = "ROUTER_LLM_MODEL",
    default_model: str = "qwen2.5:3b",
    temperature: float = 0.0,
) -> Callable[[dict], dict]:
    """
    Returns a configured predictor callable for N tools (20, 30, 50, 100)
    passing all N tools directly to the LLM in a single monolithic prompt.
    """
    global _PREDICTOR_CACHE
    if num_tools in _PREDICTOR_CACHE:
        return _PREDICTOR_CACHE[num_tools]

    tools_dict = get_tools_preset(num_tools)
    menu_lines = [f"{idx}. {name}: {desc}" for idx, (name, desc) in enumerate(tools_dict.items(), 1)]
    actions_menu = "\n".join(menu_lines)

    system_prompt = f"""You are Cozmo's baseline central routing supervisor. Your task is to accurately classify the intent of the user's message and select the exact best action from the complete list of available capabilities.

ALL AVAILABLE SYSTEM ACTIONS AND TOOLS ({num_tools} TOOLS):
{actions_menu}

CLASSIFICATION RULES:
1. SELECT THE MOST SPECIFIC ACTION: Choose the action name whose description best matches the user's explicit intent.
2. CASUAL CHAT & PERSONAL FACTS ("none"): If the user is greeting, chatting casually, stating personal facts, sharing preferences, or asking general questions not requiring external physical/system execution, select "none".
3. STRICT FORMAT: Return a structured output with the exact action name matching one of the options listed above. If no action matches, choose "none".
4. DO NOT ATTEMPT TO FULFILL THE REQUEST: Your only job is to classify and route.
"""

    router_llm = get_llm(model_env_var, default_model, temperature=temperature)
    structured_router = router_llm.with_structured_output(BaselineDecision, include_raw=True)

    def scaled_predictor(inputs: dict) -> dict:
        query = inputs["message"].strip()
        if not query:
            return {"route": "none", "reasoning": "Empty user input", "latency_ms": 0.0, "tokens_used": 0, "pipeline": f"Baseline-LLM ({num_tools} Tools)"}

        start_time = time.perf_counter()
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

            if decision and hasattr(decision, "route"):
                route = decision.route if (decision.route in tools_dict or decision.route == "none") else "none"
                reasoning = decision.reasoning or ""
            else:
                route = "none"
                reasoning = "Could not parse structured decision"
        except Exception as e:
            route = "none"
            reasoning = f"Inference exception: {str(e)}"

        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "route": route,
            "reasoning": reasoning,
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "total_tokens": tokens_used,
            "pipeline": f"Baseline-LLM ({num_tools} Tools)"
        }

    _PREDICTOR_CACHE[num_tools] = scaled_predictor
    return scaled_predictor


def test_baseline_router_wp2():
    """Pytest / Test runner entrypoint for WP2."""
    results = evaluate_router_on_wp2(
        experiment_name="Baseline-LLM",
        predictor=baseline_router_predictor,
        description="Monolithic single-shot baseline router passing all tools to LLM (qwen2.5:3b)."
    )
    assert results["total_count"] > 0, "No evaluation results returned"


if __name__ == "__main__":
    evaluate_router_on_wp2(
        experiment_name="Baseline-LLM",
        predictor=baseline_router_predictor,
        description="Monolithic single-shot baseline router passing all tools to LLM (qwen2.5:3b)."
    )
