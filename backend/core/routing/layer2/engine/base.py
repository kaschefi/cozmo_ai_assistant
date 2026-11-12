# core/routing/layer2/engine/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RouteDecisionResult:
    route: str
    confidence: float = 0.0
    raw_choice: str = ""
    details: Dict[str, Any] = None


class BaseRoutingEngine(ABC):
    """Abstract interface for query classification & tool selection engines."""

    @abstractmethod
    def select_route(
        self,
        query: str,
        active_tools: List[Dict[str, Any]],
        rag_only: bool = False
    ) -> RouteDecisionResult:
        """Evaluates query against active tools and determines the next execution route."""
        pass

