import os
import requests
from schemas.request_models import AgentState
from core.routing.tool_vector_db import tool_rag_registry
from dotenv import load_dotenv

load_dotenv()

tool_rag_registry.register_tool_schema(
    name="calendar_node",
    description="Manages Google Calendar. Use this if the user wants to check, create, move, change, or delete meetings, events, appointments, or schedules."
)
def call_n8n_calendar(user_input: str) -> str:
    """
    Sends the user's complex prompt to the n8n webhook.
    This triggers the Gemini API to extract parameters and manage the Google Calendar.
    """
    print("Routing to n8n ...")

    url = os.getenv("N8N_CALENDAR_WEBHOOK_URL", "http://localhost:5678/webhook/calendarTool")

    try:
        response = requests.post(url, json={"user_input": user_input}, timeout=180)
        response.raise_for_status()

        # We expect n8n's Webhook Response node to return a JSON object with a "response" key
        data = response.json()
        return data.get("response", "I updated the calendar, but didn't get a verbal confirmation back.")

    except requests.exceptions.Timeout:
        print("Error: n8n took too long to respond.")
        return "The calendar brain is taking too long to think. Let's try again later."

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to n8n: {e}")
        return "I'm having trouble connecting to my calendar right now. Make sure n8n is running!"

tool_rag_registry.register_tool_schema(
    name="web_search_node",
    description="Searches the live web for general real-time information, breaking news, sports updates, stock prices, or current events that alter over time."
)
def call_web_search(user_input: str) -> str:
    """
    Sends the user's complex prompt to the n8n webhook.
    This triggers the Gemini API to extract parameters and manage the Google Calendar.
    """
    print("Routing to n8n ...")

    url = os.getenv("N8N_WEBSEARCH_WEBHOOK_URL", "http://localhost:5678/webhook/websearchTool")

    try:
        response = requests.post(url, json={"user_input": user_input}, timeout=180)
        response.raise_for_status()

        # We expect n8n's Webhook Response node to return a JSON object with a "response" key
        data = response.json()
        return data.get("response")

    except requests.exceptions.Timeout:
        print("Error: n8n took too long to respond.")
        return "The brain is taking too long to think. Let's try again later."

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to n8n: {e}")
        return "I'm having trouble connecting to my web search right now. Make sure n8n is running!"