import speech_recognition as sr
import re
import asyncio
import time

WAKE_WORD = "hey buddy"

def extract_seconds(text):
    """Finds numbers and units in a sentence (e.g., '5 minutes')"""
    match = re.search(r'(\d+)\s*(hour|minute|second)', text.lower())
    if not match: return None

    number = int(match.group(1))
    unit = match.group(2)

    if "hour" in unit: return number * 3600
    if "minute" in unit: return number * 60
    return number


def start_listening_loop(loop: asyncio.AbstractEventLoop, face_library=None):
    """
    Core voice listening loop. Runs in a background thread of FastAPI
    and schedules async brain logic back to FastAPI's main event loop.
    """
    # Local imports to avoid circular dependency
    from core.routing.brain import process_user_intent

    recognizer = sr.Recognizer()
    
    # We use a try-except to handle microphone initialization issues
    try:
        microphone = sr.Microphone()
    except Exception as e:
        print(f"[Voice Listener] [Error] Could not initialize microphone: {e}")
        return

    with microphone as source:
        print("[Voice Listener] Cozmo is listening... Adjusting for ambient noise...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("[Voice Listener] Ready! Say 'Hey Buddy' followed by your command.")

        while True:
            try:
                # Capture audio from the microphone
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                text = recognizer.recognize_google(audio).lower()
                print(f" [Voice Listener] Heard: \"{text}\"")

                if WAKE_WORD in text:
                    command = text.split(WAKE_WORD, 1)[1].strip()
                    if not command:
                        print(" [Voice Listener] Wake word heard, but command was empty.")
                        continue

                    print(f" [Voice Listener] Triggering Command: \"{command}\"")

                    # Generate a unique session thread ID for this voice session
                    voice_session_id = f"voice_{int(time.time())}"

                    # Safely schedule our async process_user_intent to run in the main FastAPI loop
                    future = asyncio.run_coroutine_threadsafe(
                        process_user_intent(command, session_id=voice_session_id),
                        loop
                    )

                    # IMPORTANT: Block the listening thread until the coroutine completes.
                    # This naturally pauses the microphone while Cozmo processes the LLM response
                    # and speaks the text, preventing it from hearing itself and looping!
                    print(" [Voice Listener] Suspended microphone listening during processing...")
                    response = future.result()
                    print("[Voice Listener] Processing complete. Resuming microphone listening...")

            except sr.WaitTimeoutError:
                # No speech detected within timeout, continue listening
                continue
            except sr.UnknownValueError:
                # Speech was unintelligible, continue listening
                continue
            except Exception as e:
                print(f"[Voice Listener] Error: {e}")
                time.sleep(1)
                continue


def start_listening():
    """
    Standalone runner for local/terminal execution of voice loop.
    Creates a new event loop and runs the listener.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run the listening loop directly in the main thread (blocking)
    start_listening_loop(loop)


if __name__ == "__main__":
    start_listening()