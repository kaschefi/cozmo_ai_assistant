# backend/test/digital/routers/benchmark_dataset/tools_30.py
"""
Benchmark Test Dataset for 30 Tools Router Evaluation (Scaling Phase 1: Smart Home Expansion).

Contains 93 carefully curated evaluation utterances (3 diverse examples per route)
across 30 system tools and the conversational fallback channel.
Strict cumulative superset of tools_20.py.
"""

from typing import List, Dict

BENCHMARK_TEST_CASES: List[Dict[str, str]] = [
    # =========================================================================
    # PART 1: Physical Robot Kinematics & Docking (8 tools)
    # =========================================================================

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
    # 8. arc_sweep (Physical)
    # -------------------------------------------------------------------------
    {
        "request": "perform a visual scan of the surrounding area",
        "expected_route": "arc_sweep",
        "category": "physical"
    },
    {
        "request": "pan your camera across the room and look around",
        "expected_route": "arc_sweep",
        "category": "physical"
    },
    {
        "request": "execute a sweeping survey arc with your head and tracks",
        "expected_route": "arc_sweep",
        "category": "physical"
    },

    # =========================================================================
    # PART 2: Workstation Presets & System Utilities (5 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 9. setup_gaming (Digital Setup)
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
    # 10. setup_study (Digital Setup)
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
    # 11. setup_coding (Digital Setup)
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
    # 12. tell_time (System)
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
    # 13. get_date (System)
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

    # =========================================================================
    # PART 3: Cognitive Sub-Agents (5 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 14. calendar_node (Cognitive Agent)
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
    # 15. weather_node (Cognitive Agent)
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
    # 16. web_search_node (Cognitive Agent)
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
    # 17. code_executor_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "calculate 485 multiplied by 927",
        "expected_route": "code_executor_node",
        "category": "cognitive_agent"
    },
    {
        "request": "how many days are there between March 15 and October 31?",
        "expected_route": "code_executor_node",
        "category": "cognitive_agent"
    },
    {
        "request": "spell the word cybernetics backwards for me",
        "expected_route": "code_executor_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 18. todolist_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "add buy coffee beans to my todo list",
        "expected_route": "todolist_node",
        "category": "cognitive_agent"
    },
    {
        "request": "mark finish thesis draft as completed on my checklist",
        "expected_route": "todolist_node",
        "category": "cognitive_agent"
    },
    {
        "request": "what pending tasks do I still have left to do today?",
        "expected_route": "todolist_node",
        "category": "cognitive_agent"
    },

    # =========================================================================
    # PART 4: Media Streaming (2 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 19. spotify_play_playlist (Media)
    # -------------------------------------------------------------------------
    {
        "request": "put on my lofi hip hop playlist on Spotify",
        "expected_route": "spotify_play_playlist",
        "category": "media"
    },
    {
        "request": "play some chill instrumental study music",
        "expected_route": "spotify_play_playlist",
        "category": "media"
    },
    {
        "request": "start playing my discover weekly playlist",
        "expected_route": "spotify_play_playlist",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 20. youtube_play_video (Media)
    # -------------------------------------------------------------------------
    {
        "request": "play the latest Veritasium video on YouTube",
        "expected_route": "youtube_play_video",
        "category": "media"
    },
    {
        "request": "pull up a video tutorial about Three.js on my screen",
        "expected_route": "youtube_play_video",
        "category": "media"
    },
    {
        "request": "find and watch the trailer for Interstellar on YouTube",
        "expected_route": "youtube_play_video",
        "category": "media"
    },

    # =========================================================================
    # PART 5: Smart Home IoT Controls (10 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 21. lights_on (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "turn on the lights in the room",
        "expected_route": "lights_on",
        "category": "smart_home"
    },
    {
        "request": "it is too dark in here, please illuminate the space",
        "expected_route": "lights_on",
        "category": "smart_home"
    },
    {
        "request": "lights on please, switch the smart bulbs on",
        "expected_route": "lights_on",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 22. lights_off (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "turn off all the lights in here",
        "expected_route": "lights_off",
        "category": "smart_home"
    },
    {
        "request": "lights out, I am going to sleep now",
        "expected_route": "lights_off",
        "category": "smart_home"
    },
    {
        "request": "kill the ceiling lights and make it completely dark",
        "expected_route": "lights_off",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 23. set_light_brightness (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "dim the room lights down to thirty percent",
        "expected_route": "set_light_brightness",
        "category": "smart_home"
    },
    {
        "request": "can you make the smart bulbs a little brighter?",
        "expected_route": "set_light_brightness",
        "category": "smart_home"
    },
    {
        "request": "adjust the Hue light brightness, not my computer screen",
        "expected_route": "set_light_brightness",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 24. set_light_color (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "change the smart lights color to warm orange",
        "expected_route": "set_light_color",
        "category": "smart_home"
    },
    {
        "request": "switch the bulbs to a cool daylight white",
        "expected_route": "set_light_color",
        "category": "smart_home"
    },
    {
        "request": "make the room glow deep purple with the Hue lights",
        "expected_route": "set_light_color",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 25. activate_light_scene (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "activate the movie night lighting scene",
        "expected_route": "activate_light_scene",
        "category": "smart_home"
    },
    {
        "request": "switch the room to the reading light preset",
        "expected_route": "activate_light_scene",
        "category": "smart_home"
    },
    {
        "request": "set the ambient lighting to relax mode",
        "expected_route": "activate_light_scene",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 26. set_thermostat (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "set the thermostat to twenty-two degrees Celsius",
        "expected_route": "set_thermostat",
        "category": "smart_home"
    },
    {
        "request": "crank up the heating a little bit, it feels chilly",
        "expected_route": "set_thermostat",
        "category": "smart_home"
    },
    {
        "request": "turn down the AC to twenty degrees",
        "expected_route": "set_thermostat",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 27. get_indoor_temperature (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "what is the current temperature inside the house?",
        "expected_route": "get_indoor_temperature",
        "category": "smart_home"
    },
    {
        "request": "how warm is it in the living room right now?",
        "expected_route": "get_indoor_temperature",
        "category": "smart_home"
    },
    {
        "request": "read out the indoor humidity and room temp sensor",
        "expected_route": "get_indoor_temperature",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 28. turn_on_smart_plug (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "turn on the smart plug for the desk fan",
        "expected_route": "turn_on_smart_plug",
        "category": "smart_home"
    },
    {
        "request": "power up the outlet connected to the coffee maker",
        "expected_route": "turn_on_smart_plug",
        "category": "smart_home"
    },
    {
        "request": "switch on the plug socket to start the floor heater",
        "expected_route": "turn_on_smart_plug",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 29. turn_off_smart_plug (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "turn off the smart plug connected to the heater",
        "expected_route": "turn_off_smart_plug",
        "category": "smart_home"
    },
    {
        "request": "cut the power to the desk fan outlet",
        "expected_route": "turn_off_smart_plug",
        "category": "smart_home"
    },
    {
        "request": "switch off the wall plug socket completely",
        "expected_route": "turn_off_smart_plug",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 30. lock_door (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "lock the front door right now",
        "expected_route": "lock_door",
        "category": "smart_home"
    },
    {
        "request": "secure the house and make sure the door is locked",
        "expected_route": "lock_door",
        "category": "smart_home"
    },
    {
        "request": "engage the smart deadbolt on the front door",
        "expected_route": "lock_door",
        "category": "smart_home"
    },

    # =========================================================================
    # PART 6: Conversational Channel (1 route)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 31. none (Conversational Channel)
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
