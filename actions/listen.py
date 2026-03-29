import speech_recognition as sr
import requests
import time

WAKE_WORD = "hey buddy"
N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/cozmo-voice"


def start_listening():
    recognizer = sr.Recognizer()

    # Use the default system microphone
    with sr.Microphone() as source:
        print("Calibrating microphone for background noise... Please stay quiet for 2 seconds.")
        recognizer.adjust_for_ambient_noise(source, duration=2)
        print(f"Calibration complete! Listening for the wake word: '{WAKE_WORD}'...")

        while True:
            try:
                # Listen continuously in 5-second chunks
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)

                text = recognizer.recognize_google(audio).lower()
                print(f"You said: '{text}'")

                if WAKE_WORD in text:
                    print(f"Wake word detected!")

                    command = text.replace(WAKE_WORD, "").strip()

                    if not command:
                        print("You just said 'Cozmo' but gave no command. Ignoring.")
                        continue

                    print(f"Sending command to n8n: '{command}'")

                    # Send the text to n8n workflow
                    response = requests.post(
                        N8N_WEBHOOK_URL,
                        json={"user_input": command}
                    )

                    if response.status_code == 200:
                        print("n8n received the message!")
                    else:
                        print(f"n8n returned an error: {response.status_code}")

            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except requests.exceptions.ConnectionError:
                print("Could not connect to n8n.")
                time.sleep(5)
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    start_listening()