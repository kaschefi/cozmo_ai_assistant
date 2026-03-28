import pycozmo
import time
import os
import asyncio
import requests
import uuid
import subprocess
from pydub import AudioSegment
from core.connection import cozmo_manager
from deep_translator import GoogleTranslator

def translate_to_persian_with_ai(english_text: str) -> str:
    print(f"Translating to Persian using Gemma: '{english_text}'")
    model_name = "mshojaei77/gemma3persian"
    prompt = f"Translate the following English text to natural, conversational Persian (Farsi). Output ONLY the Persian text using the Persian alphabet. Do not include quotes, explanations, or English words.\n\nText: {english_text}"

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model_name, "prompt": prompt, "stream": False},
            timeout=20
        )
        response.raise_for_status()
        persian_text = response.json().get("response", "").strip()
        print(f"Translation result: {persian_text}")
        return persian_text
    except Exception as e:
        print(f"Translation failed: {e}")
        return english_text

def translate_to_persian_with_google(english_text: str) -> str:
    print(f"Translating to Persian using Google Translate: '{english_text}'")
    try:
        persian_text = GoogleTranslator(source='en', target='fa').translate(english_text)
        print(f"Translation result: {persian_text}")
        return persian_text
    except Exception as e:
        print(f"Translation failed: {e}")
        return english_text

def _play_audio_blocking(text: str, play_animation: bool, language: str):
    cli = cozmo_manager.get_robot()
    if not cli:
        raise Exception("Robot not connected")

    if language == "fa":
        text_to_speak = translate_to_persian_with_google(text)
        voice = "fa-IR-FaridNeural"  # Male Persian Voice
    else:
        text_to_speak = text
        voice = "en-US-ChristopherNeural"  # Male English Voice

    file_id = str(uuid.uuid4())[:8]
    temp_mp3 = f"speech_{file_id}.mp3"
    temp_wav = f"speech_{file_id}.wav"

    print(f"Step 1: Generating Edge-TTS for: {text_to_speak}")

    # Generate the speech file using Edge-TTS
    try:
        subprocess.run(
            ["edge-tts", "--voice", voice, "--text", text_to_speak, "--write-media", temp_mp3],
            check=True
        )
    except Exception as e:
        raise Exception(f"Edge-TTS failed: {e}")

    if not os.path.exists(temp_mp3) or os.path.getsize(temp_mp3) == 0:
        raise Exception("TTS failed to generate a valid audio file.")

    print("Step 2: Converting audio to Cozmo's specific 22kHz format...")
    audio = AudioSegment.from_mp3(temp_mp3)
    audio = audio.set_frame_rate(22050).set_channels(1).set_sample_width(2)
    audio.export(temp_wav, format="wav")

    if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) == 0:
        raise Exception("FFmpeg failed to convert the file to WAV.")

    print(f"Step 3: File ready! Size: {os.path.getsize(temp_wav)} bytes. Sending to Cozmo...")

    if play_animation:
        cli.move_head(1.0)
        time.sleep(0.5)

    cli.set_volume(65535)
    cli.play_audio(temp_wav)

    print("Step 4: Streaming audio to robot...")
    cli.wait_for(pycozmo.event.EvtAudioCompleted)
    print("Step 5: Audio playback complete!")

    if play_animation:
        cli.move_head(0.0)
        time.sleep(0.5)

    # Clean up
    if os.path.exists(temp_mp3):
        os.remove(temp_mp3)
    if os.path.exists(temp_wav):
        os.remove(temp_wav)

async def speak_text(text: str, play_animation: bool = True, language: str = "en"):
    try:
        await asyncio.to_thread(_play_audio_blocking, text, play_animation, language)
        return {"status": "success", "message": "Cozmo successfully spoke."}
    except Exception as e:
        print(f"Error during speech: {e}")
        return {"status": "error", "message": str(e)}