# backend/core/routing/baseline/baseline_router.py
"""
Baseline Single-Shot LLM Router.
Connects all system actions directly to the LLM with full descriptions in a single prompt
to establish an experimental baseline for comparison against the 2-layer dynamic RAG router.
"""

import time
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from core.routing.llm_factory import get_llm
from core.routing.baseline.actions_catalog import build_action_menu_string, ALL_ACTIONS_CATALOG
from core.routing.baseline.action_handlers import dispatch_action


class BaselineDecision(BaseModel):
    """Structured decision output from the monolithic baseline LLM router."""
    route: str = Field(
        description="The exact name of the chosen action/tool to execute from the catalog, or 'none' for casual chat."
    )
    reasoning: Optional[str] = Field(
        default="",
        description="A brief explanation of why this action was selected."
    )


class BaselineRouter:
    """
    Monolithic baseline router that passes all actions with full descriptions
    directly to the LLM in a single shot (no Layer 1 reflexes, no vector RAG).
    """

    def __init__(self, model_env_var: str = "ROUTER_LLM_MODEL", default_model: str = "qwen2.5:3b", temperature: float = 0.0):
        self.router_llm = get_llm(model_env_var, default_model, temperature=temperature)
        self.structured_router = self.router_llm.with_structured_output(BaselineDecision)
        self.actions_menu = build_action_menu_string()

    def _build_system_prompt(self) -> str:
        return f"""You are Cozmo's baseline central routing supervisor. Your task is to accurately classify the intent of the user's message and select the exact best action from the complete list of available capabilities.

ALL AVAILABLE SYSTEM ACTIONS AND TOOLS:
{self.actions_menu}

CLASSIFICATION RULES:
1. SELECT THE MOST SPECIFIC ACTION: Choose the action name whose description best matches the user's explicit intent.
2. CASUAL CHAT & PERSONAL FACTS ("none"): If the user is greeting, chatting casually, stating personal facts, sharing preferences, or asking general questions not requiring external physical/system execution, select "none".
3. STRICT FORMAT: Return a structured output with the exact action name matching one of the options listed above. If no action matches, choose "none".
4. DO NOT ATTEMPT TO FULFILL THE REQUEST: Your only job is to classify and route.
"""

    def classify_intent(self, user_input: str) -> BaselineDecision:
        """
        Runs monolithic single-shot classification across ALL system actions.
        Returns the structured BaselineDecision.
        """
        user_input_clean = user_input.strip()
        if not user_input_clean:
            return BaselineDecision(route="none", reasoning="Empty user input")

        system_prompt = self._build_system_prompt()
        decision = self.structured_router.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_input_clean)
        ])

        # Validate that the selected route exists in the catalog
        if decision.route not in ALL_ACTIONS_CATALOG and decision.route != "none":
            # Fallback to none if LLM hallucinated an unknown name
            return BaselineDecision(route="none", reasoning=f"Unrecognized route '{decision.route}' defaulted to none")

        return decision

    async def process_user_intent(self, command: str, mute: bool = False) -> Dict[str, Any]:
        """
        Full end-to-end baseline routing and execution pipeline.
        Measures classification latency and returns the route and response.
        """
        command_clean = command.strip()
        if not command_clean:
            return {"route": "none", "response": "", "latency_seconds": 0.0}

        start_time = time.perf_counter()
        decision = self.classify_intent(command_clean)
        latency = time.perf_counter() - start_time

        response = await dispatch_action(decision.route, command=command_clean)

        if not mute:
            try:
                from actions.physical.speak import respond
                await respond(response, mute=mute)
            except Exception:
                pass

        return {
            "route": decision.route,
            "reasoning": decision.reasoning,
            "response": response,
            "latency_seconds": latency
        }


# Singleton baseline router instance
baseline_router = BaselineRouter()


def baseline_classify_intent(user_input: str) -> BaselineDecision:
    """Convenience function for baseline intent classification."""
    return baseline_router.classify_intent(user_input)


async def baseline_process_intent(command: str, mute: bool = False) -> str:
    """Convenience function for end-to-end baseline processing."""
    res = await baseline_router.process_user_intent(command, mute=mute)
    return res.get("response", "")
