# backend/test/digital/routers/benchmark_dataset/tools_50.py
"""
Benchmark Test Dataset for 50 Tools Router Evaluation (Scaling Phase 2: Workstation & Cognitive Expansion).

Contains 153 carefully curated evaluation utterances (3 diverse examples per route)
across 50 system tools and the conversational fallback channel.
Strict cumulative superset of tools_30.py.
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
    # PART 6: Extended Desktop Automations & OS Controls (10 tools)
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
    # PART 9: Conversational Fallback Channel (1 route)
    # =========================================================================

    # -------------------------------------------------------------------------
    # 51. none (Conversational Channel)
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
