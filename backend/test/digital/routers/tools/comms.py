# backend/test/digital/routers/tools/comms.py
"""
Namespace: comms.*
Messaging, calling, and notification tools (email lives in cognitive.gmail_node).
"""

from typing import Dict, List

COMMS_NAMESPACE = "comms"

COMMS_TOOLS: Dict[str, str] = {
    "send_sms": (
        "Sends a text message (SMS) to a phone contact. "
        "Use when user says text someone, send an SMS, or message a person on their phone."
    ),
    "make_phone_call": (
        "Starts a phone call to a contact or phone number. "
        "Use when user says call someone, phone mom, or dial a number."
    ),
    "send_discord_message": (
        "Posts a message to a Discord user, server channel, or group. "
        "Use when user says message someone on Discord, post in the server, or tell the Discord group."
    ),
    "join_video_meeting": (
        "Joins an online video meeting on Zoom, Google Meet, or Microsoft Teams from a link or the next calendar meeting. "
        "Use when user says join the meeting, jump on the call, or open the Zoom link."
    ),
    "read_notifications": (
        "Reads out the latest unread notifications and messages from phone and desktop apps. "
        "Use when user asks what notifications they missed, read my alerts, or any new messages."
    ),
}

COMMS_RAG_SPECS: List[Dict[str, str]] = [
    {"name": name, "description": desc, "namespace": COMMS_NAMESPACE}
    for name, desc in COMMS_TOOLS.items()
]
