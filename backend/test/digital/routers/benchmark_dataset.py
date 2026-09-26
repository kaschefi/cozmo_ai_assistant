# backend/test/digital/routers/benchmark_dataset.py
"""
Benchmark Test Dataset for Router Evaluation.

Contains 48 carefully curated evaluation utterances (3 diverse examples per route)
across the 15 system tools and conversational fallback channel.
"""

from typing import List, Dict

BENCHMARK_TEST_CASES: List[Dict[str, str]] = [
    # -------------------------------------------------------------------------
    # 1. move_forward (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "roll straight ahead a little distance",
        "expected_route": "move_forward",
        "category": "physical"
    },
    {
        "request": "proceed forward towards the edge",
        "expected_route": "move_forward",
        "category": "physical"
    },
    {
        "request": "nudge forward just an inch",
        "expected_route": "move_forward",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 2. move_backward (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "scoot backwards away from me",
        "expected_route": "move_backward",
        "category": "physical"
    },
    {
        "request": "crawl in reverse for a moment",
        "expected_route": "move_backward",
        "category": "physical"
    },
    {
        "request": "step backward by a few centimeters",
        "expected_route": "move_backward",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 3. turn_left (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "spin counterclockwise on the spot",
        "expected_route": "turn_left",
        "category": "physical"
    },
    {
        "request": "rotate ninety degrees to your left",
        "expected_route": "turn_left",
        "category": "physical"
    },
    {
        "request": "turn to the left side please",
        "expected_route": "turn_left",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 4. turn_right (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "pivot clockwise to the right",
        "expected_route": "turn_right",
        "category": "physical"
    },
    {
        "request": "make a ninety degree right turn",
        "expected_route": "turn_right",
        "category": "physical"
    },
    {
        "request": "turn towards your right side",
        "expected_route": "turn_right",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 5. turn_around (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "do a complete one-eighty turn",
        "expected_route": "turn_around",
        "category": "physical"
    },
    {
        "request": "spin around to face backwards",
        "expected_route": "turn_around",
        "category": "physical"
    },
    {
        "request": "turn around and face the other direction",
        "expected_route": "turn_around",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 6. stop_movement (Physical - Critical Safety)
    # -------------------------------------------------------------------------
    {
        "request": "freeze right there and cut the motors",
        "expected_route": "stop_movement",
        "category": "physical"
    },
    {
        "request": "halt all movement immediately",
        "expected_route": "stop_movement",
        "category": "physical"
    },
    {
        "request": "emergency stop right now",
        "expected_route": "stop_movement",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 7. dock_with_charger (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "head back to your charging cradle",
        "expected_route": "dock_with_charger",
        "category": "physical"
    },
    {
        "request": "your battery is low so please dock yourself",
        "expected_route": "dock_with_charger",
        "category": "physical"
    },
    {
        "request": "return to home base and charge up",
        "expected_route": "dock_with_charger",
        "category": "physical"
    },

    # -------------------------------------------------------------------------
    # 8. setup_gaming (Digital Setup)
    # -------------------------------------------------------------------------
    {
        "request": "prepare my laptop so I can play video games",
        "expected_route": "setup_gaming",
        "category": "digital_setup"
    },
    {
        "request": "launch Steam and open up Discord for gaming",
        "expected_route": "setup_gaming",
        "category": "digital_setup"
    },
    {
        "request": "it is time to hop on Counter-Strike with the squad",
        "expected_route": "setup_gaming",
        "category": "digital_setup"
    },

    # -------------------------------------------------------------------------
    # 9. setup_study (Digital Setup)
    # -------------------------------------------------------------------------
    {
        "request": "get my workstation ready for my homework session",
        "expected_route": "setup_study",
        "category": "digital_setup"
    },
    {
        "request": "open up Moodle and NotebookLM so I can review notes",
        "expected_route": "setup_study",
        "category": "digital_setup"
    },
    {
        "request": "configure my screen for university study mode",
        "expected_route": "setup_study",
        "category": "digital_setup"
    },

    # -------------------------------------------------------------------------
    # 10. setup_coding (Digital Setup)
    # -------------------------------------------------------------------------
    {
        "request": "boot up PyCharm and open my GitHub repositories",
        "expected_route": "setup_coding",
        "category": "digital_setup"
    },
    {
        "request": "launch my programming tools for Python development",
        "expected_route": "setup_coding",
        "category": "digital_setup"
    },
    {
        "request": "get my coding workspace ready to write software",
        "expected_route": "setup_coding",
        "category": "digital_setup"
    },

    # -------------------------------------------------------------------------
    # 11. tell_time (System)
    # -------------------------------------------------------------------------
    {
        "request": "what is the current time of day?",
        "expected_route": "tell_time",
        "category": "system"
    },
    {
        "request": "mind telling me what the clock says?",
        "expected_route": "tell_time",
        "category": "system"
    },
    {
        "request": "can you read out the current time?",
        "expected_route": "tell_time",
        "category": "system"
    },

    # -------------------------------------------------------------------------
    # 12. get_date (System)
    # -------------------------------------------------------------------------
    {
        "request": "what date is marked on the calendar for today?",
        "expected_route": "get_date",
        "category": "system"
    },
    {
        "request": "which calendar day is today?",
        "expected_route": "get_date",
        "category": "system"
    },
    {
        "request": "could you tell me today's full date?",
        "expected_route": "get_date",
        "category": "system"
    },

    # -------------------------------------------------------------------------
    # 13. calendar_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "schedule a sync with Sarah on Wednesday at 2pm",
        "expected_route": "calendar_node",
        "category": "cognitive_agent"
    },
    {
        "request": "look up what events are on my calendar this Friday",
        "expected_route": "calendar_node",
        "category": "cognitive_agent"
    },
    {
        "request": "delete the team standup scheduled for tomorrow morning",
        "expected_route": "calendar_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 14. weather_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "is it freezing cold outside in Tokyo today?",
        "expected_route": "weather_node",
        "category": "cognitive_agent"
    },
    {
        "request": "what is the forecast and rain chance for Vienna tomorrow?",
        "expected_route": "weather_node",
        "category": "cognitive_agent"
    },
    {
        "request": "how is the weather looking in New York this weekend?",
        "expected_route": "weather_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 15. web_search_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "who won the Champions League final match?",
        "expected_route": "web_search_node",
        "category": "cognitive_agent"
    },
    {
        "request": "what are the latest breaking headlines about space exploration?",
        "expected_route": "web_search_node",
        "category": "cognitive_agent"
    },
    {
        "request": "look up the current market cap of NVIDIA",
        "expected_route": "web_search_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 16. none (Conversational Channel)
    # -------------------------------------------------------------------------
    {
        "request": "do you have any thoughts on quantum computing?",
        "expected_route": "none",
        "category": "conversational"
    },
    {
        "request": "I really enjoy drinking espresso while listening to jazz",
        "expected_route": "none",
        "category": "conversational"
    },
    {
        "request": "what kind of movies do you find most interesting?",
        "expected_route": "none",
        "category": "conversational"
    },
]
