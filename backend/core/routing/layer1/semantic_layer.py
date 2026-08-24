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
            importlib.import_module(module_name)

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


def check_layer_1(user_input: str) -> str:
    global layer_1_router
    if layer_1_router is None:
        initialize_router()
    route_choice = layer_1_router(user_input)
    return route_choice.name
