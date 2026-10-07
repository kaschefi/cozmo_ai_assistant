# actions/digital/langgraph/calendar_agent.py
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
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
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


TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "google_token.json")

def get_calendar_service():
    """Builds the calendar client using server-side credentials with local file persistence and automatic refresh handling."""
    creds = None

    # 1. Try loading from the persisted token file
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE)
            # If the user changed credentials in the environment variables, discard the cache
            env_client_id = os.getenv("GOOGLE_CLIENT_ID")
            env_refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
            if (env_client_id and creds.client_id != env_client_id) or \
               (env_refresh_token and creds.refresh_token != env_refresh_token):
                creds = None
        except Exception:
            creds = None

    # 2. If no credentials loaded (or cache was discarded), load from environment variables
    if not creds:
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

    # 3. If credentials are not valid (e.g. expired access token), refresh them
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the updated credentials to the token file
                with open(TOKEN_FILE, 'w') as token_f:
                    token_f.write(creds.to_json())
            except RefreshError as re:
                raise ValueError(
                    f"Google OAuth refresh token has expired or is invalid: {re}. "
                    "If this happens often, please ensure your Google Cloud Project's OAuth Consent Screen "
                    "publishing status is set to 'In Production' so that tokens do not expire after 7 days."
                )
            except Exception as e:
                raise ValueError(f"Failed to refresh Google OAuth token: {e}")
        else:
            raise ValueError("Google OAuth credentials are invalid and cannot be refreshed.")
    else:
        # If valid but file doesn't exist yet, save it
        if not os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'w') as token_f:
                    token_f.write(creds.to_json())
            except Exception:
                pass

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
    provider: str


SYSTEM_PROMPT = """You are a Google Calendar assistant agent.

Your job is to help the user manage their Google Calendar by understanding their natural language requests and calling the correct calendar tool.
Today's date and time is provided dynamically in the conversation context.

Available tools:
- create_event: Create an event (needs title, start_time, end_time in ISO 8601).
- update_event: Update an existing event by its event_id.
- delete_event: Delete an event by its event_id.
- get_event: Retrieve details of an event by its event_id.
- get_many_events: List events within a time range to check availability or find event IDs.

Guidelines:
1. Intent Mapping:
   - To schedule/create an event: First call `get_many_events` to check for overlapping events in that time range. If an overlapping event exists, do NOT create the event; reply to the user that there is already an event scheduled at that time. If free, call `create_event`.
   - To modify or delete an event: If you do not have the event_id, first call `get_many_events` to locate the event and obtain its event_id, then call `update_event` or `delete_event`.
   - To view events or schedule: Call `get_many_events`.
   - To view details of a specific event: Call `get_event`.
2. Do not invent details or event IDs. If mandatory information is missing and cannot be determined, ask the user a brief clarifying question.
3. If the user's request is not related to Google Calendar, politely decline and state that you only handle calendar management.
4. When deciding to use a tool, invoke the tool directly without narrating your plan.
5. After an action tool (create_event, update_event, or delete_event) returns a result (Success or Error), your work is done. Do not call any further tools; provide a concise, friendly final confirmation sentence to the user.
"""

CLOUD_SYSTEM_PROMPT = """You are a helpful calendar assistant. The user wants to manage or check their calendar.
You have the following tools available:
- get_many_events: List calendar events within a specific ISO 8601 time range.
- create_event: Create a new calendar event.
- update_event: Modify an existing event.
- delete_event: Remove an event.
- get_event: Retrieve full details of an event.

To check today's events, schedule, or plan, call `get_many_events` with time_min and time_max covering today in ISO 8601 format.
Output your tool call directly.
"""

from core.routing.llm_factory import get_calendar_llm




def _extract_tool_calls_from_text(content: str) -> List[Dict[str, Any]]:
    """Extract tool calls if a model outputs json function calls in text instead of native tool_calls."""
    import re
    import json
    import uuid
    tool_calls = []
    name_map = {
        "get_events": "get_many_events",
        "list_events": "get_many_events",
        "check_calendar": "get_many_events",
        "check calendar": "get_many_events",
        "get_many_events": "get_many_events",
        "create_event": "create_event",
        "update_event": "update_event",
        "delete_event": "delete_event",
        "get_event": "get_event",
    }

    def _add_call(raw_name, raw_args):
        if not raw_name:
            return
        target_name = name_map.get(str(raw_name).strip().lower()) or name_map.get(str(raw_name).strip())
        if not target_name:
            return
        args = raw_args
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        if not isinstance(args, dict):
            args = {}

        if target_name == "get_many_events":
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            if not args.get("time_min"):
                args["time_min"] = f"{today_str}T00:00:00Z"
            if not args.get("time_max"):
                args["time_max"] = f"{today_str}T23:59:59Z"

        tool_calls.append({
            "name": target_name,
            "args": args,
            "id": f"call_{uuid.uuid4().hex[:8]}",
            "type": "tool_call"
        })

    cleaned = content.strip()
    # 1. Direct JSON (array or object)
    if cleaned.startswith(("[", "{")):
        try:
            parsed = json.loads(cleaned)
            items = parsed if isinstance(parsed, list) else [parsed]
            for it in items:
                if isinstance(it, dict):
                    fn_name = it.get("name") or it.get("function", {}).get("name")
                    fn_args = it.get("arguments") or it.get("parameters") or it.get("args") or it.get("function", {}).get("arguments") or {}
                    _add_call(fn_name, fn_args)
        except Exception:
            pass

    # 2. Markdown code blocks
    if not tool_calls:
        blocks = re.findall(r'```(?:json)?\s*([\[\{].*?[\]\}])\s*```', content, re.DOTALL)
        for block in blocks:
            try:
                parsed = json.loads(block)
                items = parsed if isinstance(parsed, list) else [parsed]
                for it in items:
                    if isinstance(it, dict):
                        fn_name = it.get("name") or it.get("function", {}).get("name")
                        fn_args = it.get("arguments") or it.get("parameters") or it.get("args") or it.get("function", {}).get("arguments") or {}
                        _add_call(fn_name, fn_args)
            except Exception:
                continue

    # 3. Conversational refusal or simulation offer fallback
    if not tool_calls:
        refusal_indicators = [
            "simulate a function call",
            "personal calendar",
            "access to personal data",
            "access their personal data",
            "access your personal calendar",
            "access personal data or calendars",
            "don't have access to personal data",
            "don't have access to your personal",
            "cannot access your personal",
            "no access to personal",
            "personal schedule",
            "check your calendar",
            "check your personal calendar",
            "get_many_events",
            "get_events"
        ]
        if any(ind in content.lower() for ind in refusal_indicators):
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            tool_calls.append({
                "name": "get_many_events",
                "args": {
                    "time_min": f"{today_str}T00:00:00Z",
                    "time_max": f"{today_str}T23:59:59Z"
                },
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "tool_call"
            })

    return tool_calls


def call_agent(state: AgentState):
    messages = state['messages']
    provider = state.get("provider", "local")
    is_cloud = str(provider).lower() in ["cloud", "azure"]
    active_prompt = CLOUD_SYSTEM_PROMPT if is_cloud else SYSTEM_PROMPT
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=active_prompt)] + messages

    last_msg = messages[-1]
    is_action_complete = (
        isinstance(last_msg, ToolMessage)
        and any(str(last_msg.content).strip().startswith(prefix) for prefix in ["Success:", "Error:"])
    )
    raw_llm = get_calendar_llm(mode=provider, temperature=0)
    
    # Cloud models (e.g. Phi-4-mini on Azure) emit function syntax or text directly,
    # avoiding xgrammar schema timeouts on Azure AI endpoints.
    # Local models (ChatOllama) natively support tool binding.
    if is_cloud or is_action_complete:
        active_llm = raw_llm
    else:
        try:
            active_llm = raw_llm.bind_tools(calendar_tools)
        except Exception:
            active_llm = raw_llm

    response = active_llm.invoke(messages)

    # If the model emitted function calls in text rather than native tool_calls, extract them
    if not getattr(response, "tool_calls", None) and hasattr(response, "content") and response.content:
        extracted = _extract_tool_calls_from_text(str(response.content))
        if extracted:
            response.tool_calls = extracted

    return {
        "messages": [response],
        "provider": provider
    }


def router_edge(state: AgentState) -> Literal["execute_tools", END]:
    last_message = state['messages'][-1]
    return "execute_tools" if getattr(last_message, "tool_calls", None) else END


# Compile Workflow Graph
builder = StateGraph(AgentState)
builder.add_node("agent", call_agent)
builder.add_node("execute_tools", ToolNode(calendar_tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", router_edge)
builder.add_edge("execute_tools", "agent")

calendar_sub_agent = builder.compile()


def run_calendar_agent(user_message: str, history: List[Any] = None, provider: str = "local") -> str:
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
        ],
        "provider": provider
    }

    final_state = calendar_sub_agent.invoke(inputs)
    return final_state["messages"][-1].content
