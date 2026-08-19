# backend/core/routing/baseline/__init__.py
"""
Baseline routing package for MoKa AI Assistant.
Provides monolithic all-tools single-shot LLM routing for benchmark comparison.
"""

from core.routing.baseline.actions_catalog import (
    ALL_ACTIONS_CATALOG,
    get_all_action_names,
    build_action_menu_string,
)
from core.routing.baseline.action_handlers import (
    BASELINE_ACTION_HANDLERS,
    dispatch_action,
)
from core.routing.baseline.baseline_router import (
    BaselineDecision,
    BaselineRouter,
    baseline_router,
    baseline_classify_intent,
    baseline_process_intent,
)

__all__ = [
    "ALL_ACTIONS_CATALOG",
    "get_all_action_names",
    "build_action_menu_string",
    "BASELINE_ACTION_HANDLERS",
    "dispatch_action",
    "BaselineDecision",
    "BaselineRouter",
    "baseline_router",
    "baseline_classify_intent",
    "baseline_process_intent",
]
