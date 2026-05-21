import importlib
import pkgutil
import logging
from semantic_router.encoders import FastEmbedEncoder
from semantic_router.routers import SemanticRouter
from core.registry import reflex_registry
import actions.physical
import actions.digital

logging.getLogger("semantic_router").setLevel(logging.ERROR)

layer_1_router = None

def load_actions():
    """
    Automatically imports all modules inside the actions packages
    so that the decorators trigger and register themselves.
    """
    for package in [actions.physical, actions.digital]:
        for _, module_name, _ in pkgutil.iter_packages(package.__path__, package.__name__ + "."):
            importlib.import_module(module_name)

def initialize_router():
    global layer_1_router

    print("Discovering local actions...")
    load_actions()

    print("Loading FastEmbed Encoder...")
    encoder = FastEmbedEncoder(name="BAAI/bge-large-en-v1.5")

    print(f"Building Semantic Index with {len(reflex_registry.routes)} registered routes...")
    layer_1_router = SemanticRouter(
        encoder=encoder,
        routes=reflex_registry.routes,
        auto_sync="local"
    )

initialize_router()


async def execute_reflex(route_name: str) -> bool:
    if route_name in reflex_registry.actions:
        action_func, speech_text = reflex_registry.actions[route_name]
        print(f"Executing Reflex: {route_name}")

        if speech_text:
            print(speech_text)

        if action_func:
            await action_func()
        return True
    return False


def check_layer_1(user_input: str) -> str:
    route_choice = layer_1_router(user_input)
    return route_choice.name