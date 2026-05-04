import requests
from schemas.request_models import AgentState
import requests


def call_n8n_calendar(user_input: str) -> str:
    """
    Sends the user's complex prompt to the n8n webhook.
    This triggers the Gemini API to extract parameters and manage the Google Calendar.
    """
    print("Routing to n8n ...")

    url = "http://localhost:5678/webhook/calendarTool"

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

