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

from semantic_router.encoders import FastEmbedEncoder
from semantic_router.routers import SemanticRouter
from core.routing.registry import reflex_registry
import actions.physical
import actions.digital

layer_1_router = None

def load_actions():
    """
    Automatically imports all modules inside the actions packages
    so that the decorators trigger and register themselves.
    """
    for package in [actions.physical, actions.digital]:
        for _, module_name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            importlib.import_module(module_name)

def initialize_router():
    global layer_1_router

    load_actions()
    encoder = FastEmbedEncoder(name="BAAI/bge-small-en-v1.5")
    layer_1_router = SemanticRouter(
        encoder=encoder,
        routes=reflex_registry.routes,
        auto_sync="local",
        aggregation="max"
    )

    # Build Layer 2 Tool RAG index exactly once after all actions are registered
    from core.routing.tool_vector_db import tool_rag_registry
    tool_rag_registry.build_index()

initialize_router()


async def execute_reflex(route_name: str) -> bool:
    if route_name in reflex_registry.actions:
        action_func, speech_text = reflex_registry.actions[route_name]
        print(f"Executing Reflex: {route_name}")

        if speech_text:
            from actions.physical.speak import respond
            await respond(speech_text)

        if action_func:
            await action_func()
        return True
    return False


def check_layer_1(user_input: str) -> str:
    route_choice = layer_1_router(user_input)
    return route_choice.name