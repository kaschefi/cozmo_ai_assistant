# core/routing/layer1/semantic_layer.py
import importlib
import pkgutil
import logging
import warnings
import os

# Suppress all python warnings and disable log levels below ERROR globally
warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

# Silently disable all tqdm progress bars (e.g. from FastEmbed/Hugging Face downloads)
try:
    import tqdm
    original_init = tqdm.tqdm.__init__
    def new_init(self, *args, **kwargs):
        kwargs['disable'] = True
        original_init(self, *args, **kwargs)
    tqdm.tqdm.__init__ = new_init
except Exception:
    pass

from core.routing.encoder import get_shared_encoder
from semantic_router.routers import SemanticRouter
from core.routing.layer1.registry import reflex_registry
import actions.physical
import actions.digital

layer_1_router = None

def load_actions():
    """
    Automatically imports all modules inside the actions packages and subpackages
    so that the decorators trigger and register themselves.
    """
    for package in [actions.physical, actions.digital]:
        for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                importlib.import_module(module_name)
            except Exception:
                pass

def initialize_router():
    global layer_1_router

    load_actions()
    encoder = get_shared_encoder()
    layer_1_router = SemanticRouter(
        encoder=encoder,
        routes=reflex_registry.routes,
        auto_sync="local",
        aggregation="max"
    )

    # Build Layer 2 Tool RAG index exactly once after all actions are registered
    from core.routing.layer2.tool_vector_db import tool_rag_registry
    tool_rag_registry.load_dormant_catalog()
    tool_rag_registry.build_index()

async def execute_reflex(route_name: str, mute: bool = False) -> tuple[bool, str]:
    if route_name in reflex_registry.actions:
        action_func, speech_text = reflex_registry.actions[route_name]
        print(f"Executing Reflex: {route_name}")
        result_msg = speech_text or ""

        if speech_text:
            from actions.physical.speak import respond
            await respond(speech_text, mute=mute)

        if action_func:
            import inspect
            sig = inspect.signature(action_func)
            if "mute" in sig.parameters:
                res = await action_func(mute=mute)
            else:
                res = await action_func()

            if isinstance(res, str) and res:
                result_msg = res
            elif isinstance(res, dict) and "status" in res:
                result_msg = f"{route_name}: {res.get('status')}"
            elif not result_msg:
                result_msg = f"Executed reflex: {route_name}"

        return True, result_msg
    return False, ""


def validate_layer_1_reflex(layer_1_route: str | None, query: str) -> str | None:
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


def check_layer_1(user_input: str) -> str | None:
    global layer_1_router
    if layer_1_router is None:
        initialize_router()
    route_choice = layer_1_router(user_input)
    route_name = route_choice.name if route_choice else None
    return validate_layer_1_reflex(route_name, user_input)
