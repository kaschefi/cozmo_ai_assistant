# backend/test/digital/routers/tools/companion.py
"""
Namespace: companion.*
Cozmo personality behaviors: jokes, games, dances, and emotional animations.
"""

from typing import Dict, List

COMPANION_NAMESPACE = "companion"

COMPANION_TOOLS: Dict[str, str] = {
    "tell_joke": (
        "Makes the Cozmo robot tell a short joke or funny pun out loud. "
        "Use when user says tell me a joke, make me laugh, or say something funny."
    ),
    "play_speed_tap": (
        "Starts the Speed Tap reflex game with the Cozmo robot using its light cubes. "
        "Use when user wants to play a game with the robot, play speed tap, or challenge Cozmo."
    ),
    "play_memory_match": (
        "Starts a cube light-pattern Memory Match game against the Cozmo robot. "
        "Use when user says play memory match, memory game, or remember the pattern with the robot."
    ),
    "do_a_dance": (
        "Makes the Cozmo robot perform a dance routine with wheels, head, and lift movements. "
        "Use when user says dance, show me your moves, or do a little dance."
    ),
    "play_happy_animation": (
        "Plays a happy, excited, or victory animation on the Cozmo robot. "
        "Use when user says be happy, celebrate, cheer, or do a victory dance."
    ),
    "play_sad_animation": (
        "Plays a sad, disappointed, or pouting animation on the Cozmo robot. "
        "Use when user says act sad, pout, look disappointed, or show you are upset."
    ),
}

COMPANION_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": COMPANION_NAMESPACE}
    for name, desc in COMPANION_TOOLS.items()
]
