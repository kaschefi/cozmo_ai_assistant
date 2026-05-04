from semantic_router import Route
from semantic_router.encoders import FastEmbedEncoder
from semantic_router.routers import SemanticRouter
from actions.physical.charger import dock_with_charger
from actions.physical.speak import speak_text

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
routes = [dock_route, stop_route, time_route, date_route]

print("Loading FastEmbed Encoder...")
encoder = FastEmbedEncoder(name="BAAI/bge-small-en-v1.5")

layer_1_router = SemanticRouter(encoder=encoder, routes=routes, auto_sync="local")


REFLEX_REGISTRY = {
    "dock_with_charger": (dock_with_charger, "Heading back to base!"),
    # "stop_motors": (stop_motors, "Stopping!"),
    # "tell_joke": (tell_joke, "Here is a good one...")
}


async def execute_reflex(route_name: str) -> bool:
    """
    Looks up the route in the registry and executes it dynamically.
    Returns True if a reflex was executed, False if not.
    """
    if route_name in REFLEX_REGISTRY:
        action_func, speech_text = REFLEX_REGISTRY[route_name]

        print(f"Executing Reflex: {route_name} (Latency: ~50ms)")

        # Say the catchphrase
        if speech_text:
            await speak_text(speech_text)

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