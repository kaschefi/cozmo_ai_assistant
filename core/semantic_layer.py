from semantic_router import Route
from semantic_router.encoders import FastEmbedEncoder
from semantic_router.routers import SemanticRouter
from actions.physical.charger import dock_with_charger
import os
from actions.physical.speak import speak_text
from actions.digital.setups import setup_gaming, setup_study, setup_coding
import logging


logging.getLogger("semantic_router").setLevel(logging.ERROR)

dock_route = Route(
    name="dock_with_charger",
    score_threshold=0.9,
    utterances=[
        "go to sleep",
        "go to your charger",
        "dock yourself",
        "your battery is low",
        "return to base",
        "find the charger",
    ],
)

stop_route = Route(
    name="stop_motors",
    score_threshold=0.9,
    utterances=[
        "stop",
        "freeze",
        "halt",
        "don't move",
        "stop moving immediately",
        "cut the motors",
        "stop all movement",
        "stop driving",
    ],
)

time_route = Route(
    name="tell_time",
    score_threshold=0.9,
    utterances=[
        "what time is it",
        "tell me the time",
        "current time",
        "what's the time right now",
    ],
)
date_route = Route(
    name="get_date",
    score_threshold=0.9,
    utterances=[
        "what is the date",
        "what is today",
        "tell me the date",
        "what day is it today",
        "current date"
    ]
)
gaming_route = Route(
    name="setup_gaming",
    score_threshold=0.8,
    utterances=[
        "set my laptop for gaming",
        "gaming mode",
        "open steam and discord",
        "time to game",
        "prepare for gaming",
        "setups game",
        "gaming work",
    ],
)
coding_route = Route(
    name="setup_coding",
    score_threshold=0.8,
    utterances=[
        "set my laptop for coding",
        "coding mode",
        "time to code",
        "prepare for coding",
        "setups code",
    ],
)

study_route = Route(
    name="setup_study",
    score_threshold=0.8,
    utterances=[
        "set it for study",
        "study mode",
        "time to study",
        "prepare my laptop for study",
        "open my study tabs",
        "study work",
        "setups study",
    ],
)
routes = [dock_route, stop_route, time_route, date_route, gaming_route, study_route, coding_route]

layer_1_router = None


def initialize_router():
    global layer_1_router

    print("Loading FastEmbed Encoder (Waking up the local brain)...")
    encoder = FastEmbedEncoder(name="BAAI/bge-small-en-v1.5")

    print("Building Semantic Index in memory...")
    layer_1_router = SemanticRouter(encoder=encoder, routes=routes, auto_sync="local")

    print("Layer 1 Router is ready!")

initialize_router()

REFLEX_REGISTRY = {
    "dock_with_charger": (dock_with_charger, "Heading back to base!"),
    # "stop_motors": (stop_motors, "Stopping!"),
    # "tell_joke": (tell_joke, "Here is a good one...")
    "setup_gaming": (setup_gaming, "Game on! Setting up your laptop for gaming."),
    "setup_study": (setup_study, "Focus time! Opening your study materials."),
    "setup_coding": (setup_coding, "Coding time! Setting up your laptop for coding."),
}


async def execute_reflex(route_name: str) -> bool:
    """
    Looks up the route in the registry and executes it dynamically.
    Returns True if a reflex was executed, False if not.
    """
    if route_name in REFLEX_REGISTRY:
        action_func, speech_text = REFLEX_REGISTRY[route_name]

        print(f"Executing Reflex: {route_name}")

        # Say the catchphrase
        if speech_text:
            print(speech_text)

        # Execute the action
        if action_func:
            await action_func()

        return True

    return False

def check_layer_1(user_input: str) -> str:
    """
    Checks if the input matches a fast Layer 1 reflex.
    Returns the name of the route, or None if no match is found.
    """
    route_choice = layer_1_router(user_input)
    return route_choice.name