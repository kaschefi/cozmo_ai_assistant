from datetime import datetime
from core.routing.layer1.registry import reflex_registry
from core.routing.layer2.tool_vector_db import tool_rag_registry
from actions.physical.speak import respond

tool_rag_registry.register_tool_schema(
    name="tell_time",
    description="Provides the current local time (hour and minute). Use when the user asks what time it is, what hour it is, or to check the clock."
)
tool_rag_registry.register_tool_schema(
    name="get_date",
    description="Provides today's full calendar date and day of the week. Use when the user asks for today's date, day of month, or calendar day."
)

@reflex_registry.reflex(
    name="tell_time",
    score_threshold=0.86,
    utterances=[
        "what time is it",
        "what time is it right now",
        "tell me the time",
        "what is the current time",
        "tell me the current time",
        "what's the time right now",
        "can you tell me the current time",
        "what's the time on the clock",
        "time right now",
    ]
)
async def tell_time(mute: bool = False):
    current_time = datetime.now().strftime("%I:%M %p")
    msg = f"The time is exactly {current_time}."
    await respond(msg, mute=mute)
    return msg

@reflex_registry.reflex(
    name="get_date",
    score_threshold=0.84,
    utterances=[
        "what is the date",
        "what is today",
        "what is today's date",
        "tell me the date",
        "what day is it today",
        "what day of the week is it today",
        "tell me the full date today",
        "what's the date today",
    ]
)
async def get_date(mute: bool = False):
    today = datetime.now().strftime("%A, %B %d, %Y")
    msg = f"Today is {today}."
    await respond(msg, mute=mute)
    return msg