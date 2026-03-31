import speech_recognition as sr
import requests
import re

WAKE_WORD = "hey buddy"
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/cozmo-voice"
FASTAPI_TIMER_URL = "http://localhost:8000/actions/timer"


def extract_seconds(text):
    """Finds numbers and units in a sentence (e.g., '5 minutes')"""
    match = re.search(r'(\d+)\s*(hour|minute|second)', text.lower())
    if not match: return None

    number = int(match.group(1))
    unit = match.group(2)

    if "hour" in unit: return number * 3600
    if "minute" in unit: return number * 60
    return number


def start_listening():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Cozmo is listening...")
        recognizer.adjust_for_ambient_noise(source, duration=1)

        while True:
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                text = recognizer.recognize_google(audio).lower()
                print(f"Heard: {text}")

                if WAKE_WORD in text:
                    command = text.replace(WAKE_WORD, "").strip()

                    #  CHECK FOR TIMER
                    if "timer" in command:
                        seconds = extract_seconds(command)
                        if seconds:
                            print(f"Timer detected ({seconds}s). Sending to FastAPI...")
                            requests.post(FASTAPI_TIMER_URL, json={"seconds": seconds})
                            continue  # Skip n8n

                    #  EVERYTHING ELSE (n8n Route)
                    print("Sending to n8n brain...")
                    requests.post(N8N_WEBHOOK_URL, json={"user_input": command})

            except Exception:
                continue


if __name__ == "__main__":
    start_listening()