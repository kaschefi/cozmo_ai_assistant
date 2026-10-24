# backend/test/digital/routers/tools/smart_home.py
"""
Namespace: smart_home.*
Smart home IoT controls (Philips Hue lights, thermostat, plugs, locks, blinds).
Synthetic tools for scaling experiments.
"""

from typing import Dict, List

SMART_HOME_NAMESPACE = "smart_home"

SMART_HOME_TOOLS: Dict[str, str] = {
    "lights_on": (
        "Turns on the room lights through Philips Hue. "
        "Use when user says turn on the lights, lights on, or light up the room."
    ),
    "lights_off": (
        "Turns off the room lights through Philips Hue. "
        "Use when user says turn off the lights, lights out, or kill the lights."
    ),
    "set_light_brightness": (
        "Dims or brightens the room lights to a percentage level. "
        "Use when user says dim the lights, make the lights brighter, or set lights to 50 percent."
    ),
    "set_light_color": (
        "Changes the color or color temperature of the smart bulbs. "
        "Use when user says make the lights blue, warm white, cool white, or change the bulb color."
    ),
    "activate_light_scene": (
        "Activates a saved lighting scene such as movie, reading, relax, or party. "
        "Use when user says set the movie scene, reading lights, or party lighting."
    ),
    "set_thermostat": (
        "Sets the home thermostat target temperature in Celsius. "
        "Use when user says make it warmer, set the heating to 22 degrees, or turn the AC down."
    ),
    "get_indoor_temperature": (
        "Reports the current temperature and humidity inside the house from the thermostat sensor. "
        "Use when user asks how warm it is inside, room temperature, or indoor humidity."
    ),
    "turn_on_smart_plug": (
        "Switches on a smart plug and the appliance connected to it, such as a lamp, fan, or coffee machine. "
        "Use when user says turn on the fan, power on the coffee machine, or plug on."
    ),
    "turn_off_smart_plug": (
        "Switches off a smart plug and the appliance connected to it. "
        "Use when user says turn off the fan, power off the heater, or plug off."
    ),
    "lock_door": (
        "Locks the smart front door lock. "
        "Use when user says lock the door, secure the house, or did I lock up."
    ),
    "unlock_door": (
        "Unlocks the smart front door lock after confirmation. "
        "Use when user says unlock the door, let someone in, or open the front door lock."
    ),
    "set_blinds": (
        "Opens or closes the motorized window blinds or curtains. "
        "Use when user says open the blinds, close the curtains, or let some sunlight in."
    ),
}

SMART_HOME_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": SMART_HOME_NAMESPACE}
    for name, desc in SMART_HOME_TOOLS.items()
]
