# backend/test/digital/routers/benchmark_dataset/tools_100.py
"""
Benchmark Test Dataset for 100 Tools Router Evaluation (Complete Scaling Stress Test).

Contains 303 carefully curated evaluation utterances (3 diverse examples per route)
across all 100 system tools and the conversational fallback channel.
Strict cumulative superset of tools_50.py, tools_30.py, and tools_20.py.
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
    # PART 2: Base Workstation Presets & System Utilities (5 tools)
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
    # PART 3: Base Cognitive Sub-Agents (5 tools)
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
    # PART 4: Base Media Streaming (2 tools)
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
    # PART 5: Base Smart Home IoT Controls (10 tools)
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
    # PART 6: Desktop Automations & OS Controls (10 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 31. set_system_volume (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "turn the volume up on my computer",
        "expected_route": "set_system_volume",
        "category": "desktop"
    },
    {
        "request": "set the laptop speaker volume to seventy percent",
        "expected_route": "set_system_volume",
        "category": "desktop"
    },
    {
        "request": "make the PC louder, not Cozmo's speaker",
        "expected_route": "set_system_volume",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 32. mute_system_audio (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "mute the computer audio right now",
        "expected_route": "mute_system_audio",
        "category": "desktop"
    },
    {
        "request": "silence all sound output on the laptop",
        "expected_route": "mute_system_audio",
        "category": "desktop"
    },
    {
        "request": "unmute the PC speakers so I can hear",
        "expected_route": "mute_system_audio",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 33. adjust_screen_brightness (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "dim the laptop screen, it is hurting my eyes",
        "expected_route": "adjust_screen_brightness",
        "category": "desktop"
    },
    {
        "request": "turn up the display brightness to maximum",
        "expected_route": "adjust_screen_brightness",
        "category": "desktop"
    },
    {
        "request": "the screen is too dark, brighten the monitor",
        "expected_route": "adjust_screen_brightness",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 34. toggle_dark_mode (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "switch the computer to dark mode",
        "expected_route": "toggle_dark_mode",
        "category": "desktop"
    },
    {
        "request": "turn on the light theme for the system",
        "expected_route": "toggle_dark_mode",
        "category": "desktop"
    },
    {
        "request": "toggle between dark and light appearance for Windows",
        "expected_route": "toggle_dark_mode",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 35. take_screenshot (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "take a screenshot of what is currently on my screen",
        "expected_route": "take_screenshot",
        "category": "desktop"
    },
    {
        "request": "capture the desktop display and save the image",
        "expected_route": "take_screenshot",
        "category": "desktop"
    },
    {
        "request": "grab a screen capture of this window",
        "expected_route": "take_screenshot",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 36. lock_screen (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "lock my computer screen, I am stepping away",
        "expected_route": "lock_screen",
        "category": "desktop"
    },
    {
        "request": "lock the laptop session for security",
        "expected_route": "lock_screen",
        "category": "desktop"
    },
    {
        "request": "lock the PC until I come back",
        "expected_route": "lock_screen",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 37. put_computer_to_sleep (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "put the laptop to sleep",
        "expected_route": "put_computer_to_sleep",
        "category": "desktop"
    },
    {
        "request": "suspend the computer until tomorrow morning",
        "expected_route": "put_computer_to_sleep",
        "category": "desktop"
    },
    {
        "request": "put the PC into sleep mode",
        "expected_route": "put_computer_to_sleep",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 38. shutdown_computer (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "shut down my laptop completely",
        "expected_route": "shutdown_computer",
        "category": "desktop"
    },
    {
        "request": "power off the computer for the night",
        "expected_route": "shutdown_computer",
        "category": "desktop"
    },
    {
        "request": "restart the PC after installing updates",
        "expected_route": "shutdown_computer",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 39. open_application (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "open the Calculator app on my desktop",
        "expected_route": "open_application",
        "category": "desktop"
    },
    {
        "request": "launch Google Chrome on the laptop",
        "expected_route": "open_application",
        "category": "desktop"
    },
    {
        "request": "start the Notepad text editor program",
        "expected_route": "open_application",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 40. setup_meeting (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "prepare my workstation for an upcoming video meeting",
        "expected_route": "setup_meeting",
        "category": "desktop"
    },
    {
        "request": "activate meeting mode and get my camera and mic ready",
        "expected_route": "setup_meeting",
        "category": "desktop"
    },
    {
        "request": "get my desk set up for a Zoom call with the team",
        "expected_route": "setup_meeting",
        "category": "desktop"
    },

    # =========================================================================
    # PART 7: Extended Cognitive Sub-Agents (5 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 41. gmail_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "check my Gmail inbox for any unread messages from my professor",
        "expected_route": "gmail_node",
        "category": "cognitive_agent"
    },
    {
        "request": "draft a quick email reply to Alex confirming the appointment",
        "expected_route": "gmail_node",
        "category": "cognitive_agent"
    },
    {
        "request": "search my emails for the conference flight ticket confirmation",
        "expected_route": "gmail_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 42. maps_directions_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "how long does it take to drive to Vienna Airport from downtown?",
        "expected_route": "maps_directions_node",
        "category": "cognitive_agent"
    },
    {
        "request": "give me walking directions to the nearest train station",
        "expected_route": "maps_directions_node",
        "category": "cognitive_agent"
    },
    {
        "request": "what is the fastest route to get to Stephansplatz right now?",
        "expected_route": "maps_directions_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 43. translation_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "translate this sentence into German for me",
        "expected_route": "translation_node",
        "category": "cognitive_agent"
    },
    {
        "request": "how do you say thank you very much for your help in Japanese?",
        "expected_route": "translation_node",
        "category": "cognitive_agent"
    },
    {
        "request": "what does the French phrase c'est la vie mean in English?",
        "expected_route": "translation_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 44. summarizer_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "give me a short summary of this research paper abstract",
        "expected_route": "summarizer_node",
        "category": "cognitive_agent"
    },
    {
        "request": "what is the TL;DR of this long news article?",
        "expected_route": "summarizer_node",
        "category": "cognitive_agent"
    },
    {
        "request": "condense this technical text into three key bullet points",
        "expected_route": "summarizer_node",
        "category": "cognitive_agent"
    },

    # -------------------------------------------------------------------------
    # 45. contacts_node (Cognitive Agent)
    # -------------------------------------------------------------------------
    {
        "request": "what is Christoph's phone number in my contacts?",
        "expected_route": "contacts_node",
        "category": "cognitive_agent"
    },
    {
        "request": "look up Sarah's email address from my address book",
        "expected_route": "contacts_node",
        "category": "cognitive_agent"
    },
    {
        "request": "find the contact details and birthday for Michael",
        "expected_route": "contacts_node",
        "category": "cognitive_agent"
    },

    # =========================================================================
    # PART 8: Productivity Tools (5 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 46. set_timer (Productivity)
    # -------------------------------------------------------------------------
    {
        "request": "set a timer for fifteen minutes",
        "expected_route": "set_timer",
        "category": "productivity"
    },
    {
        "request": "countdown forty-five seconds starting now",
        "expected_route": "set_timer",
        "category": "productivity"
    },
    {
        "request": "start a twenty-minute kitchen timer for the pasta",
        "expected_route": "set_timer",
        "category": "productivity"
    },

    # -------------------------------------------------------------------------
    # 47. set_alarm (Productivity)
    # -------------------------------------------------------------------------
    {
        "request": "set an alarm for seven-thirty tomorrow morning",
        "expected_route": "set_alarm",
        "category": "productivity"
    },
    {
        "request": "wake me up at six AM sharp",
        "expected_route": "set_alarm",
        "category": "productivity"
    },
    {
        "request": "schedule an alarm clock alert for eight in the morning",
        "expected_route": "set_alarm",
        "category": "productivity"
    },

    # -------------------------------------------------------------------------
    # 48. cancel_alarm (Productivity)
    # -------------------------------------------------------------------------
    {
        "request": "cancel my seven AM alarm",
        "expected_route": "cancel_alarm",
        "category": "productivity"
    },
    {
        "request": "turn off the running kitchen countdown timer",
        "expected_route": "cancel_alarm",
        "category": "productivity"
    },
    {
        "request": "disable all active morning alarms",
        "expected_route": "cancel_alarm",
        "category": "productivity"
    },

    # -------------------------------------------------------------------------
    # 49. create_reminder (Productivity)
    # -------------------------------------------------------------------------
    {
        "request": "remind me in two hours to drink water",
        "expected_route": "create_reminder",
        "category": "productivity"
    },
    {
        "request": "set a reminder for five PM to take out the trash",
        "expected_route": "create_reminder",
        "category": "productivity"
    },
    {
        "request": "remind me after thirty minutes to check the oven",
        "expected_route": "create_reminder",
        "category": "productivity"
    },

    # -------------------------------------------------------------------------
    # 50. start_pomodoro (Productivity)
    # -------------------------------------------------------------------------
    {
        "request": "start a pomodoro session for my study sprint",
        "expected_route": "start_pomodoro",
        "category": "productivity"
    },
    {
        "request": "begin a twenty-five minute focus work interval",
        "expected_route": "start_pomodoro",
        "category": "productivity"
    },
    {
        "request": "start the pomodoro productivity timer with short breaks",
        "expected_route": "start_pomodoro",
        "category": "productivity"
    },

    # =========================================================================
    # PART 9: Extended Cozmo Robot Actions (18 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 51. say_text (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "make Cozmo say hello world out loud",
        "expected_route": "say_text",
        "category": "robot"
    },
    {
        "request": "speak the phrase good morning everyone through your robot speaker",
        "expected_route": "say_text",
        "category": "robot"
    },
    {
        "request": "repeat after me: welcome to my thesis defense",
        "expected_route": "say_text",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 52. set_robot_volume (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "turn up the Cozmo robot speaker volume",
        "expected_route": "set_robot_volume",
        "category": "robot"
    },
    {
        "request": "make Cozmo speak a bit quieter",
        "expected_route": "set_robot_volume",
        "category": "robot"
    },
    {
        "request": "adjust the robot audio level, not my laptop speakers",
        "expected_route": "set_robot_volume",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 53. show_oled_face_expression (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "show happy eyes on your face display",
        "expected_route": "show_oled_face_expression",
        "category": "robot"
    },
    {
        "request": "make a surprised expression on your OLED screen",
        "expected_route": "show_oled_face_expression",
        "category": "robot"
    },
    {
        "request": "look angry with your digital eyes",
        "expected_route": "show_oled_face_expression",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 54. raise_lift (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "lift your forklift arm all the way up",
        "expected_route": "raise_lift",
        "category": "robot"
    },
    {
        "request": "raise your front loader arm",
        "expected_route": "raise_lift",
        "category": "robot"
    },
    {
        "request": "lift up your front forklift",
        "expected_route": "raise_lift",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 55. lower_lift (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "lower your forklift arm down to the table",
        "expected_route": "lower_lift",
        "category": "robot"
    },
    {
        "request": "put your front lift back down to the ground",
        "expected_route": "lower_lift",
        "category": "robot"
    },
    {
        "request": "drop the forklift arm flat",
        "expected_route": "lower_lift",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 56. tilt_head_up (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "tilt your head and camera up towards the ceiling",
        "expected_route": "tilt_head_up",
        "category": "robot"
    },
    {
        "request": "look upwards with your camera",
        "expected_route": "tilt_head_up",
        "category": "robot"
    },
    {
        "request": "angle your robot head up to see my face",
        "expected_route": "tilt_head_up",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 57. tilt_head_down (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "tilt your head down to look at the desk",
        "expected_route": "tilt_head_down",
        "category": "robot"
    },
    {
        "request": "look downward with your front camera",
        "expected_route": "tilt_head_down",
        "category": "robot"
    },
    {
        "request": "angle your camera down towards your tracks",
        "expected_route": "tilt_head_down",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 58. find_cube (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "find your nearest light cube on the desk",
        "expected_route": "find_cube",
        "category": "robot"
    },
    {
        "request": "look around and drive up to one of your blocks",
        "expected_route": "find_cube",
        "category": "robot"
    },
    {
        "request": "locate your interactive cube without picking it up",
        "expected_route": "find_cube",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 59. pick_up_cube (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "pick up the light cube with your lift arm",
        "expected_route": "pick_up_cube",
        "category": "robot"
    },
    {
        "request": "grab the block in front of you and lift it",
        "expected_route": "pick_up_cube",
        "category": "robot"
    },
    {
        "request": "scoop up the cube with your forklift",
        "expected_route": "pick_up_cube",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 60. place_cube_down (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "put down the cube you are carrying",
        "expected_route": "place_cube_down",
        "category": "robot"
    },
    {
        "request": "release the block onto the tabletop",
        "expected_route": "place_cube_down",
        "category": "robot"
    },
    {
        "request": "set the carried cube down gently",
        "expected_route": "place_cube_down",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 61. stack_cubes (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "stack one cube on top of the other cube",
        "expected_route": "stack_cubes",
        "category": "robot"
    },
    {
        "request": "build a two-cube tower with your blocks",
        "expected_route": "stack_cubes",
        "category": "robot"
    },
    {
        "request": "place the block you are holding onto the other block",
        "expected_route": "stack_cubes",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 62. roll_cube (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "roll the light cube over onto its side",
        "expected_route": "roll_cube",
        "category": "robot"
    },
    {
        "request": "flip the block with your lift arm",
        "expected_route": "roll_cube",
        "category": "robot"
    },
    {
        "request": "push the cube so it tumbles over",
        "expected_route": "roll_cube",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 63. pop_a_wheelie (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "pop a wheelie with your tracks",
        "expected_route": "pop_a_wheelie",
        "category": "robot"
    },
    {
        "request": "do a trick and stand up on your back wheels",
        "expected_route": "pop_a_wheelie",
        "category": "robot"
    },
    {
        "request": "balance up on your rear treads using the cube",
        "expected_route": "pop_a_wheelie",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 64. set_backpack_lights (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "change your backpack lights to bright cyan",
        "expected_route": "set_backpack_lights",
        "category": "robot"
    },
    {
        "request": "set the LEDs on your back to green",
        "expected_route": "set_backpack_lights",
        "category": "robot"
    },
    {
        "request": "turn off your back LEDs completely",
        "expected_route": "set_backpack_lights",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 65. toggle_head_light (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "turn on your infrared headlight for night vision",
        "expected_route": "toggle_head_light",
        "category": "robot"
    },
    {
        "request": "switch on the front IR camera light",
        "expected_route": "toggle_head_light",
        "category": "robot"
    },
    {
        "request": "turn off your front headlight LED",
        "expected_route": "toggle_head_light",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 66. take_photo (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "take a picture with your robot camera",
        "expected_route": "take_photo",
        "category": "robot"
    },
    {
        "request": "snap a photo of what Cozmo sees right now",
        "expected_route": "take_photo",
        "category": "robot"
    },
    {
        "request": "capture an image from your front camera and save it",
        "expected_route": "take_photo",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 67. find_face (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "scan around for human faces and see who is there",
        "expected_route": "find_face",
        "category": "robot"
    },
    {
        "request": "look for my face and say hello when you see me",
        "expected_route": "find_face",
        "category": "robot"
    },
    {
        "request": "turn around to detect if someone is looking at you",
        "expected_route": "find_face",
        "category": "robot"
    },

    # -------------------------------------------------------------------------
    # 68. check_robot_battery (Robot)
    # -------------------------------------------------------------------------
    {
        "request": "what is the Cozmo robot battery level?",
        "expected_route": "check_robot_battery",
        "category": "robot"
    },
    {
        "request": "check if the robot battery voltage is low",
        "expected_route": "check_robot_battery",
        "category": "robot"
    },
    {
        "request": "how much charge does Cozmo have left?",
        "expected_route": "check_robot_battery",
        "category": "robot"
    },

    # =========================================================================
    # PART 10: Additional Desktop OS Controls (5 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 69. close_application (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "close the Chrome browser on my desktop",
        "expected_route": "close_application",
        "category": "desktop"
    },
    {
        "request": "quit Spotify and close the window",
        "expected_route": "close_application",
        "category": "desktop"
    },
    {
        "request": "force quit the running Calculator app",
        "expected_route": "close_application",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 70. toggle_wifi (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "turn off the Wi-Fi on my laptop",
        "expected_route": "toggle_wifi",
        "category": "desktop"
    },
    {
        "request": "enable the wireless network adapter",
        "expected_route": "toggle_wifi",
        "category": "desktop"
    },
    {
        "request": "disconnect from Wi-Fi on this PC",
        "expected_route": "toggle_wifi",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 71. toggle_bluetooth (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "turn on Bluetooth on my computer",
        "expected_route": "toggle_bluetooth",
        "category": "desktop"
    },
    {
        "request": "disable the laptop Bluetooth adapter",
        "expected_route": "toggle_bluetooth",
        "category": "desktop"
    },
    {
        "request": "enable Bluetooth so I can connect my headphones",
        "expected_route": "toggle_bluetooth",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 72. toggle_do_not_disturb (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "turn on Do Not Disturb mode on my laptop",
        "expected_route": "toggle_do_not_disturb",
        "category": "desktop"
    },
    {
        "request": "mute all Windows desktop notifications so I can focus",
        "expected_route": "toggle_do_not_disturb",
        "category": "desktop"
    },
    {
        "request": "disable Focus Assist and turn alerts back on",
        "expected_route": "toggle_do_not_disturb",
        "category": "desktop"
    },

    # -------------------------------------------------------------------------
    # 73. get_system_stats (Desktop)
    # -------------------------------------------------------------------------
    {
        "request": "how much RAM and CPU is the laptop using right now?",
        "expected_route": "get_system_stats",
        "category": "desktop"
    },
    {
        "request": "check available disk space and memory on my PC",
        "expected_route": "get_system_stats",
        "category": "desktop"
    },
    {
        "request": "what is the laptop battery percentage and performance stats?",
        "expected_route": "get_system_stats",
        "category": "desktop"
    },

    # =========================================================================
    # PART 11: Extended Media & Spotify Controls (12 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 74. spotify_resume_track (Media)
    # -------------------------------------------------------------------------
    {
        "request": "resume the paused song on Spotify",
        "expected_route": "spotify_resume_track",
        "category": "media"
    },
    {
        "request": "unpause my music playback",
        "expected_route": "spotify_resume_track",
        "category": "media"
    },
    {
        "request": "continue playing the track where I left off",
        "expected_route": "spotify_resume_track",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 75. spotify_pause_playback (Media)
    # -------------------------------------------------------------------------
    {
        "request": "pause the music on Spotify",
        "expected_route": "spotify_pause_playback",
        "category": "media"
    },
    {
        "request": "stop playing the song for a minute",
        "expected_route": "spotify_pause_playback",
        "category": "media"
    },
    {
        "request": "pause playback on my speakers",
        "expected_route": "spotify_pause_playback",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 76. spotify_next_track (Media)
    # -------------------------------------------------------------------------
    {
        "request": "skip to the next song on Spotify",
        "expected_route": "spotify_next_track",
        "category": "media"
    },
    {
        "request": "next track please, I don't like this song",
        "expected_route": "spotify_next_track",
        "category": "media"
    },
    {
        "request": "play the next track in the queue",
        "expected_route": "spotify_next_track",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 77. spotify_previous_track (Media)
    # -------------------------------------------------------------------------
    {
        "request": "go back to the previous song on Spotify",
        "expected_route": "spotify_previous_track",
        "category": "media"
    },
    {
        "request": "replay the last track from the beginning",
        "expected_route": "spotify_previous_track",
        "category": "media"
    },
    {
        "request": "restart this song or play the previous one",
        "expected_route": "spotify_previous_track",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 78. spotify_set_volume (Media)
    # -------------------------------------------------------------------------
    {
        "request": "turn up the volume inside the Spotify app",
        "expected_route": "spotify_set_volume",
        "category": "media"
    },
    {
        "request": "set the Spotify player volume to fifty percent",
        "expected_route": "spotify_set_volume",
        "category": "media"
    },
    {
        "request": "make the music softer in Spotify, not master Windows volume",
        "expected_route": "spotify_set_volume",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 79. spotify_toggle_shuffle (Media)
    # -------------------------------------------------------------------------
    {
        "request": "turn on shuffle mode for this playlist on Spotify",
        "expected_route": "spotify_toggle_shuffle",
        "category": "media"
    },
    {
        "request": "disable shuffle and play the album in order",
        "expected_route": "spotify_toggle_shuffle",
        "category": "media"
    },
    {
        "request": "turn on repeat for the currently playing song",
        "expected_route": "spotify_toggle_shuffle",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 80. spotify_like_song (Media)
    # -------------------------------------------------------------------------
    {
        "request": "like this song on Spotify",
        "expected_route": "spotify_like_song",
        "category": "media"
    },
    {
        "request": "save this track to my favorite songs library",
        "expected_route": "spotify_like_song",
        "category": "media"
    },
    {
        "request": "add the currently playing song to my liked tracks",
        "expected_route": "spotify_like_song",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 81. spotify_play_artist (Media)
    # -------------------------------------------------------------------------
    {
        "request": "play songs by Daft Punk on Spotify",
        "expected_route": "spotify_play_artist",
        "category": "media"
    },
    {
        "request": "put on some Coldplay music",
        "expected_route": "spotify_play_artist",
        "category": "media"
    },
    {
        "request": "shuffle tracks by Hans Zimmer",
        "expected_route": "spotify_play_artist",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 82. spotify_add_to_queue (Media)
    # -------------------------------------------------------------------------
    {
        "request": "add Bohemian Rhapsody to my Spotify queue",
        "expected_route": "spotify_add_to_queue",
        "category": "media"
    },
    {
        "request": "queue up this song to play next after the current one",
        "expected_route": "spotify_add_to_queue",
        "category": "media"
    },
    {
        "request": "put this track into the upcoming queue",
        "expected_route": "spotify_add_to_queue",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 83. spotify_now_playing (Media)
    # -------------------------------------------------------------------------
    {
        "request": "what song is currently playing on Spotify?",
        "expected_route": "spotify_now_playing",
        "category": "media"
    },
    {
        "request": "who sings this track and what is the album name?",
        "expected_route": "spotify_now_playing",
        "category": "media"
    },
    {
        "request": "tell me the artist and title of the current song",
        "expected_route": "spotify_now_playing",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 84. play_podcast (Media)
    # -------------------------------------------------------------------------
    {
        "request": "play the latest episode of the Lex Fridman podcast",
        "expected_route": "play_podcast",
        "category": "media"
    },
    {
        "request": "put on the Huberman Lab podcast show",
        "expected_route": "play_podcast",
        "category": "media"
    },
    {
        "request": "start streaming my favorite tech podcast",
        "expected_route": "play_podcast",
        "category": "media"
    },

    # -------------------------------------------------------------------------
    # 85. set_music_sleep_timer (Media)
    # -------------------------------------------------------------------------
    {
        "request": "stop playing music after forty-five minutes",
        "expected_route": "set_music_sleep_timer",
        "category": "media"
    },
    {
        "request": "set a thirty-minute sleep timer for Spotify",
        "expected_route": "set_music_sleep_timer",
        "category": "media"
    },
    {
        "request": "fade out and turn off the music in an hour",
        "expected_route": "set_music_sleep_timer",
        "category": "media"
    },

    # =========================================================================
    # PART 12: Additional Smart Home Controls (2 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 86. unlock_door (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "unlock the front door for the guest",
        "expected_route": "unlock_door",
        "category": "smart_home"
    },
    {
        "request": "open the smart deadbolt to let my friend in",
        "expected_route": "unlock_door",
        "category": "smart_home"
    },
    {
        "request": "unlock the front entrance lock",
        "expected_route": "unlock_door",
        "category": "smart_home"
    },

    # -------------------------------------------------------------------------
    # 87. set_blinds (Smart Home)
    # -------------------------------------------------------------------------
    {
        "request": "open the motorized window blinds to let light in",
        "expected_route": "set_blinds",
        "category": "smart_home"
    },
    {
        "request": "close the living room smart shades",
        "expected_route": "set_blinds",
        "category": "smart_home"
    },
    {
        "request": "lower the window blinds all the way down",
        "expected_route": "set_blinds",
        "category": "smart_home"
    },

    # =========================================================================
    # PART 13: Companion Personality, Games & Animations (6 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 88. tell_joke (Companion)
    # -------------------------------------------------------------------------
    {
        "request": "tell me a funny programming joke",
        "expected_route": "tell_joke",
        "category": "companion"
    },
    {
        "request": "make me laugh with a witty pun",
        "expected_route": "tell_joke",
        "category": "companion"
    },
    {
        "request": "say something humorous to cheer me up",
        "expected_route": "tell_joke",
        "category": "companion"
    },

    # -------------------------------------------------------------------------
    # 89. play_speed_tap (Companion)
    # -------------------------------------------------------------------------
    {
        "request": "let's play the Speed Tap game with your cubes",
        "expected_route": "play_speed_tap",
        "category": "companion"
    },
    {
        "request": "challenge Cozmo to a reflex tap match",
        "expected_route": "play_speed_tap",
        "category": "companion"
    },
    {
        "request": "start a game of speed tap against the robot",
        "expected_route": "play_speed_tap",
        "category": "companion"
    },

    # -------------------------------------------------------------------------
    # 90. play_memory_match (Companion)
    # -------------------------------------------------------------------------
    {
        "request": "start a game of Memory Match with your light cubes",
        "expected_route": "play_memory_match",
        "category": "companion"
    },
    {
        "request": "let's play the light sequence pattern remembering game",
        "expected_route": "play_memory_match",
        "category": "companion"
    },
    {
        "request": "play memory match and test my pattern recall",
        "expected_route": "play_memory_match",
        "category": "companion"
    },

    # -------------------------------------------------------------------------
    # 91. do_a_dance (Companion)
    # -------------------------------------------------------------------------
    {
        "request": "do a little victory dance with your tracks and lift",
        "expected_route": "do_a_dance",
        "category": "companion"
    },
    {
        "request": "show me your dance moves Cozmo",
        "expected_route": "do_a_dance",
        "category": "companion"
    },
    {
        "request": "dance to the beat of the music",
        "expected_route": "do_a_dance",
        "category": "companion"
    },

    # -------------------------------------------------------------------------
    # 92. play_happy_animation (Companion)
    # -------------------------------------------------------------------------
    {
        "request": "act happy and celebrate with an excited animation",
        "expected_route": "play_happy_animation",
        "category": "companion"
    },
    {
        "request": "cheer for me and show your happy celebration animation",
        "expected_route": "play_happy_animation",
        "category": "companion"
    },
    {
        "request": "play a victory excited celebration routine",
        "expected_route": "play_happy_animation",
        "category": "companion"
    },

    # -------------------------------------------------------------------------
    # 93. play_sad_animation (Companion)
    # -------------------------------------------------------------------------
    {
        "request": "play a disappointed pouting animation",
        "expected_route": "play_sad_animation",
        "category": "companion"
    },
    {
        "request": "act sad and look dejected",
        "expected_route": "play_sad_animation",
        "category": "companion"
    },
    {
        "request": "show that you are feeling upset with an animation",
        "expected_route": "play_sad_animation",
        "category": "companion"
    },

    # =========================================================================
    # PART 14: Communications & Messaging (5 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 94. send_sms (Comms)
    # -------------------------------------------------------------------------
    {
        "request": "send an SMS text message to my mom",
        "expected_route": "send_sms",
        "category": "comms"
    },
    {
        "request": "text David saying I will be there in ten minutes",
        "expected_route": "send_sms",
        "category": "comms"
    },
    {
        "request": "send a text message to his mobile number",
        "expected_route": "send_sms",
        "category": "comms"
    },

    # -------------------------------------------------------------------------
    # 95. make_phone_call (Comms)
    # -------------------------------------------------------------------------
    {
        "request": "call Christoph on his mobile phone",
        "expected_route": "make_phone_call",
        "category": "comms"
    },
    {
        "request": "dial mom's phone number and start the call",
        "expected_route": "make_phone_call",
        "category": "comms"
    },
    {
        "request": "place a phone call to the doctor's office",
        "expected_route": "make_phone_call",
        "category": "comms"
    },

    # -------------------------------------------------------------------------
    # 96. send_discord_message (Comms)
    # -------------------------------------------------------------------------
    {
        "request": "send a message in our Discord gaming server channel",
        "expected_route": "send_discord_message",
        "category": "comms"
    },
    {
        "request": "post an update to the Discord study group chat",
        "expected_route": "send_discord_message",
        "category": "comms"
    },
    {
        "request": "message my friend on Discord asking if he wants to play",
        "expected_route": "send_discord_message",
        "category": "comms"
    },

    # -------------------------------------------------------------------------
    # 97. join_video_meeting (Comms)
    # -------------------------------------------------------------------------
    {
        "request": "join my upcoming Google Meet video call right now",
        "expected_route": "join_video_meeting",
        "category": "comms"
    },
    {
        "request": "open the Zoom link from my calendar and connect",
        "expected_route": "join_video_meeting",
        "category": "comms"
    },
    {
        "request": "hop on the Microsoft Teams call that is starting",
        "expected_route": "join_video_meeting",
        "category": "comms"
    },

    # -------------------------------------------------------------------------
    # 98. read_notifications (Comms)
    # -------------------------------------------------------------------------
    {
        "request": "read out my latest unread phone and desktop notifications",
        "expected_route": "read_notifications",
        "category": "comms"
    },
    {
        "request": "what alerts and app messages did I miss?",
        "expected_route": "read_notifications",
        "category": "comms"
    },
    {
        "request": "check my recent notification tray and read them aloud",
        "expected_route": "read_notifications",
        "category": "comms"
    },

    # =========================================================================
    # PART 15: Additional Productivity Tools (2 tools)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 99. take_note (Productivity)
    # -------------------------------------------------------------------------
    {
        "request": "take a quick note: thesis defense date is in March",
        "expected_route": "take_note",
        "category": "productivity"
    },
    {
        "request": "jot down this idea for my research paper",
        "expected_route": "take_note",
        "category": "productivity"
    },
    {
        "request": "write this down in my personal notes list",
        "expected_route": "take_note",
        "category": "productivity"
    },

    # -------------------------------------------------------------------------
    # 100. read_notes (Productivity)
    # -------------------------------------------------------------------------
    {
        "request": "read back my saved notes from this week",
        "expected_route": "read_notes",
        "category": "productivity"
    },
    {
        "request": "what notes do I have stored about my thesis?",
        "expected_route": "read_notes",
        "category": "productivity"
    },
    {
        "request": "search my personal notes for the book recommendation",
        "expected_route": "read_notes",
        "category": "productivity"
    },

    # =========================================================================
    # PART 16: Conversational Fallback Channel (1 route)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 101. none (Conversational Channel)
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
