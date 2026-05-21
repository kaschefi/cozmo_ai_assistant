# core/registry.py
from semantic_router import Route


class ReflexRegistry:
    def __init__(self):
        self.routes = []
        # Maps route_name (function, speech_text)
        self.actions = {}

    def reflex(self, name: str, utterances: list[str], score_threshold: float = 0.85, speech: str = ""):
        """
        Decorator to register a low-latency reflex action.
        """

        def decorator(func):
            # Create the Semantic Router Route object
            route_obj = Route(
                name=name,
                utterances=utterances,
                score_threshold=score_threshold
            )
            self.routes.append(route_obj)

            # Map the route name to its execution logic
            self.actions[name] = (func, speech)
            return func

        return decorator


# Create a singleton instance to use across project
reflex_registry = ReflexRegistry()