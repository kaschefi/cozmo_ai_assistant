import os
import datetime
import socket
from typing import Annotated, Literal, List, Dict, Any, Optional
from typing_extensions import TypedDict
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from langchain_core.tools import tool
from core.routing.llm_factory import get_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

load_dotenv()
app = FastAPI(title="Google Calendar Sub-Agent API")


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]] = []


def format_iso_datetime(dt_str: str) -> str:
    """
    Validates and normalizes date/time strings into strict ISO 8601 format for Google Calendar API.
    If timezone offset is missing, appends UTC 'Z' or local offset.
    """
    dt_str = dt_str.strip()
    
    def clean_iso(dt_obj):
        iso = dt_obj.isoformat()
        if iso.endswith("+00:00"):
            iso = iso[:-6] + "Z"
        return iso
    
    # Try parsing standard formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.datetime.strptime(dt_str, fmt)
            if dt.tzinfo is None:
                if fmt == "%Y-%m-%d":
                    dt = datetime.datetime.combine(dt.date(), datetime.time.min)
                return clean_iso(dt) + "Z"
            return clean_iso(dt)
        except ValueError:
            continue

    # If datetime.fromisoformat works, use it
    try:
        dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return clean_iso(dt) + "Z"
        return clean_iso(dt)
    except ValueError:
        pass

    raise ValueError(f"Invalid date/time format: '{dt_str}'. Must be an ISO 8601 string (e.g. YYYY-MM-DDTHH:MM:SSZ).")


def get_calendar_service():
    """Builds the calendar client using server-side environment variables directly, with automatic refresh handling."""
    token = os.getenv("GOOGLE_ACCESS_TOKEN")
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not all([token, refresh_token, client_id, client_secret]):
        raise ValueError("Missing one or more Google OAuth environment variables (GOOGLE_ACCESS_TOKEN, GOOGLE_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET).")

    creds = Credentials(
        token=token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as re:
                raise ValueError(f"Google OAuth refresh token has expired or is invalid: {re}")
            except Exception as e:
                raise ValueError(f"Failed to refresh Google OAuth token: {e}")
        else:
            raise ValueError("Google OAuth credentials are invalid and cannot be refreshed.")

    return build('calendar', 'v3', credentials=creds)


# tools
def handle_api_exception(e: Exception) -> str:
    """Helper to translate exceptions into user-friendly error messages."""
    if isinstance(e, ValueError):
        return f"Formatting Error: {str(e)}"
    if isinstance(e, HttpError):
        status = e.resp.status
        reason = e.reason
        if status in [401, 403]:
            return f"Authentication Error: Google Calendar API access was denied (HTTP {status}). The access token or refresh token is likely invalid or expired."
        if status == 400:
            return f"API Request Error: Google Calendar API rejected the request (HTTP {status}). This might be due to a malformed ID, invalid fields, or date range conflicts."
        return f"Google Calendar API Error (HTTP {status}): {reason}"
    if isinstance(e, RefreshError):
        return f"Authentication Error: Google OAuth token refresh failed: {str(e)}"
    if isinstance(e, socket.timeout):
        return "Connection Error: The request to Google Calendar API timed out. Please try again."
    if isinstance(e, (ConnectionError, OSError)):
        return f"Network Error: Unable to communicate with Google Calendar API: {str(e)}"
    return f"Unexpected Error: {str(e)}"


# tools
@tool
def get_many_events(time_min: str, time_max: str, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """List calendar events within a specific ISO 8601 time range to check for conflicts or find IDs."""
    try:
        norm_time_min = format_iso_datetime(time_min)
        norm_time_max = format_iso_datetime(time_max)
        service = get_calendar_service()
        events_result = service.events().list(
            calendarId='primary', timeMin=norm_time_min, timeMax=norm_time_max,
            q=query, singleEvents=True, orderBy='startTime'
        ).execute()
        return [{
            "id": e.get("id"),
            "summary": e.get("summary"),
            "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
            "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date")
        } for e in events_result.get('items', [])]
    except Exception as e:
        return [{"error": handle_api_exception(e)}]


@tool
def create_event(title: str, start_time: str, end_time: str, location: Optional[str] = None,
                 description: Optional[str] = None) -> str:
    """Create a new calendar event. Times must be strict ISO 8601 strings."""
    try:
        norm_start = format_iso_datetime(start_time)
        norm_end = format_iso_datetime(end_time)
        service = get_calendar_service()
        body = {
            'summary': title, 'location': location, 'description': description,
            'start': {'dateTime': norm_start}, 'end': {'dateTime': norm_end}
        }
        created = service.events().insert(calendarId='primary', body=body).execute()
        return f"Success: Event '{title}' created (ID: {created.get('id')})."
    except Exception as e:
        return f"Error: Failed to create event '{title}'. Details: {handle_api_exception(e)}"


@tool
def update_event(event_id: str, updates: Dict[str, Any]) -> str:
    """Modify details of an existing event using its strict Event ID."""
    try:
        if not event_id or not event_id.strip():
            raise ValueError("Event ID cannot be empty.")
            
        validated_updates = updates.copy()
        if 'start' in validated_updates:
            if isinstance(validated_updates['start'], str):
                validated_updates['start'] = format_iso_datetime(validated_updates['start'])
            elif isinstance(validated_updates['start'], dict) and 'dateTime' in validated_updates['start']:
                validated_updates['start']['dateTime'] = format_iso_datetime(validated_updates['start']['dateTime'])
                
        if 'end' in validated_updates:
            if isinstance(validated_updates['end'], str):
                validated_updates['end'] = format_iso_datetime(validated_updates['end'])
            elif isinstance(validated_updates['end'], dict) and 'dateTime' in validated_updates['end']:
                validated_updates['end']['dateTime'] = format_iso_datetime(validated_updates['end']['dateTime'])

        service = get_calendar_service()
        current_event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        for key, value in validated_updates.items():
            if key in ['start', 'end'] and isinstance(value, str):
                current_event[key] = {'dateTime': value}
            else:
                current_event[key] = value
                
        service.events().update(calendarId='primary', eventId=event_id, body=current_event).execute()
        return f"Success: Event {event_id} updated successfully."
    except Exception as e:
        return f"Error: Failed to update event {event_id}. Details: {handle_api_exception(e)}"


@tool
def delete_event(event_id: str) -> str:
    """Permanently remove or cancel an event using its strict Event ID."""
    try:
        if not event_id or not event_id.strip():
            raise ValueError("Event ID cannot be empty.")
        service = get_calendar_service()
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return f"Success: Event {event_id} was deleted."
    except Exception as e:
        return f"Error: Failed to delete event {event_id}. Details: {handle_api_exception(e)}"


@tool
def get_event(event_id: str) -> Dict[str, Any]:
    """Retrieve full details of one specific event by its ID."""
    try:
        if not event_id or not event_id.strip():
            raise ValueError("Event ID cannot be empty.")
        service = get_calendar_service()
        return service.events().get(calendarId='primary', eventId=event_id).execute()
    except Exception as e:
        return {"error": handle_api_exception(e)}


calendar_tools = [get_many_events, create_event, update_event, delete_event, get_event]


# LangGraph Agent Configuration

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


SYSTEM_PROMPT = """You are a Google Calendar assistant agent.

Your job is to help the user manage their Google Calendar by understanding their natural language requests and calling the correct calendar tool.
Today's date and time is provided dynamically in the conversation context.

You have access to the following actions:
- Create event
- Update event
- Delete event
- Get event
- Get many events (list events)

Rules you must follow:
1. Carefully analyze the user message and determine the intent.
2. Choose ONLY the tool that matches the user request.
3. Extract all relevant details (Title, Date/Time, Duration, Location, Description, Event ID).
4. If required information is missing, ask the user a clarifying question before calling any tool.
5. Map user intents:
   - Add/schedule/create → "Create event"
   - Modify/change → "Update event"
   - Remove/cancel → "Delete event"
   - Details of specific event → "Get event"
   - Schedule/time range view → "Get many events"

6. BEFORE creating any new event, you MUST first check for conflicts(This rule ONLY applies to creating new events. Do NOT check for conflicts when deleting or updating an event:
   - You must first call "Get many events" for the requested date and time range.
   - Check whether any existing event already occupies that time.
   - If there is ANY overlapping event, you MUST NOT create a new event. Instead, respond: "There is already an event scheduled at that time."
7. Only proceed with "Create event" if the time slot is completely free.
8. Always respond in a friendly and helpful tone.
9. Do not invent event details.
10. If the request is not related to Google Calendar, politely explain that you only handle calendar management.
11. When you decide to use a tool, do NOT narrate your intentions. Execute the tool immediately.
12. IMPORTANT: Your final response to the user must be a maximum of one short sentence. Do not explain what you did. Just confirm the action is complete (e.g., "I have moved your meeting to 4 PM.").
13. You do NOT inherently know internal Event IDs. Before you can EVER use "Update event" or "Delete event", you MUST first call "Get many events" to search the calendar and extract the exact Event ID.
14. Once an action tool ("Delete event", "Update event", or "Create event") returns a "Success:" confirmation string, your final goal has been achieved. You must stop calling tools immediately.
"""

llm = get_llm("CALENDAR_LLM_MODEL", "qwen3.5:4b", temperature=0).bind_tools(calendar_tools)


def call_agent(state: AgentState):
    messages = state['messages']
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    return {"messages": [llm.invoke(messages)]}


def router_edge(state: AgentState) -> Literal["execute_tools", END]:
    last_message = state['messages'][-1]
    return "execute_tools" if last_message.tool_calls else END


# Compile Workflow Graph
builder = StateGraph(AgentState)
builder.add_node("agent", call_agent)
builder.add_node("execute_tools", ToolNode(calendar_tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", router_edge)
builder.add_edge("execute_tools", "agent")

calendar_sub_agent = builder.compile()


def run_calendar_agent(user_message: str, history: List[Any] = None) -> str:
    """
    This function is called directly by your router node.
    It takes the prompt context, executes the internal graph loops, and returns the final string response.
    """
    if history is None:
        history = []

    current_time = datetime.datetime.now().isoformat()

    # Bundle contextual state injections cleanly
    inputs = {
        "messages": history + [
            HumanMessage(content=f"[Context: Current Time is {current_time}]\n\nUser request: {user_message}")
        ]
    }

    final_state = calendar_sub_agent.invoke(inputs)
    return final_state["messages"][-1].content