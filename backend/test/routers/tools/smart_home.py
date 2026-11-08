# backend/test/routers/tools/smart_home.py
"""
Namespace: smart_home.*
Smart home IoT controls (Philips Hue lights, thermostat, plugs, locks, blinds).
Synthetic tools for scaling experiments.
"""

from typing import Dict, List

SMART_HOME_NAMESPACE = "smart_home"

SMART_HOME_TOOLS: Dict[str, str] = {
    "lights_on": (
        "Switches on power to smart room lights. "
        "Use when user says turn on the lights, lights on, or light up the room. Power switch on only."
    ),
    "lights_off": (
        "Switches off the power to room lights. "
        "Use when user says turn off the lights, lights out, or kill the lights. Power switch off only."
    ),
    "set_light_brightness": (
        "Makes the lights brighter, dims the room lights down, or sets brightness level. "
        "Use when user says make the lights brighter, brighten, dim the room lights down, or change illumination brightness."
    ),
    "set_light_color": (
        "Changes the RGB color hue or color temperature of smart light bulbs. "
        "Use when user specifies a color or color tone: warm orange, cool daylight white, deep purple, blue, green, red, yellow, or changing bulb colors."
    ),
    "activate_light_scene": (
        "Activates a named ambient lighting scene, mood preset, or profile. "
        "Use when user asks for a preset or scene mode: reading light preset, relax mode, movie scene, party lighting, or ambient lighting profiles."
    ),
    "set_thermostat": (
        "Controls climate control, AC, and heating setpoint in Celsius degrees. "
        "Use when user says turn down the AC, crank up the heating, make it warmer or cooler, or set thermostat temperature to degrees (e.g. 20 degrees, 22 degrees)."
    ),
    "get_indoor_temperature": (
        "Queries and reports current indoor temperature, indoor humidity, or thermostat sensor readings. "
        "Use when user asks what the temperature inside is, how warm it is in the house, or to read indoor humidity and room temp sensor."
    ),
    "turn_on_smart_plug": (
        "Powers on an electrical smart plug socket or wall outlet connected to appliances. "
        "Use when user wants to power up an outlet, switch on a wall plug socket, turn on the fan outlet, start floor heater via plug, or power on the coffee maker socket."
    ),
    "turn_off_smart_plug": (
        "Cuts power to an electrical smart plug socket or wall outlet. "
        "Use when user says cut power to desk fan outlet, switch off wall plug socket completely, turn off smart plug connected to heater, or power down an electrical socket."
    ),
    "lock_door": (
        "Locks the smart physical front door lock. "
        "Use when user says lock the front door, secure the house and make sure the door is locked, or lock up."
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
