from datetime import datetime
from core.registry import reflex_registry
from actions.physical.speak import speak_text

@reflex_registry.reflex(
    name="tell_time",
    score_threshold=0.9,
    utterances=[
        "what time is it",
        "tell me the time",
        "current time",
        "what's the time right now"
    ]
)
async def tell_time():
    current_time = datetime.now().strftime("%I:%M %p")
    msg = f"The time is exactly {current_time}."
    print(msg)
    await speak_text(msg, language="en")

@reflex_registry.reflex(
    name="get_date",
    score_threshold=0.9,
    utterances=[
        "what is the date",
        "what is today",
        "tell me the date",
        "what day is it today"
    ]
)
async def get_date():
    today = datetime.now().strftime("%A, %B %d, %Y")
    msg = f"Today is {today}."
    print(msg)
    await speak_text(msg, language="en")