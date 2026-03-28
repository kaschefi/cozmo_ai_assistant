import pycozmo
import time
import os
import asyncio
import requests
import uuid
import edge_tts
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


def convert_to_cozmo_format(temp_mp3: str, temp_wav: str):
    print("Converting to 22kHz WAV...")
    audio = AudioSegment.from_mp3(temp_mp3)

    silence = AudioSegment.silent(duration=500)
    audio = silence + audio

    audio = audio.set_frame_rate(22050).set_channels(1).set_sample_width(2)
    audio.export(temp_wav, format="wav")
    os.remove(temp_mp3)


def _play_audio_blocking(wav_file: str, play_animation: bool):
    cli = cozmo_manager.get_robot()
    if not cli:
        raise Exception("Robot not connected")

    if play_animation:
        cli.move_head(1.0)
        time.sleep(0.5)

    print("Streaming to Cozmo...")
    cli.set_volume(65535)
    cli.play_audio(wav_file)
    cli.wait_for(pycozmo.event.EvtAudioCompleted)

    if play_animation:
        cli.move_head(0.0)
        time.sleep(0.5)

    # Delete the final WAV file only after Cozmo finishes talking
    if os.path.exists(wav_file):
        os.remove(wav_file)


async def speak_text(text: str, play_animation: bool = True, language: str = "en"):
    try:
        start_time = time.time()

        #Get Translation (Run in background thread)
        if language == "fa":
            text_to_speak = await asyncio.to_thread(translate_to_persian_with_google, text)
            voice = "fa-IR-FaridNeural"
        else:
            text_to_speak = text
            voice = "en-US-ChristopherNeural"

        file_id = str(uuid.uuid4())[:8]
        temp_mp3 = f"speech_{file_id}.mp3"
        temp_wav = f"speech_{file_id}.wav"

        print("Generating Edge-TTS audio...")
        communicate = edge_tts.Communicate(text_to_speak, voice)
        await communicate.save(temp_mp3)

        # Convert Audio Format (Run in background thread)
        await asyncio.to_thread(convert_to_cozmo_format, temp_mp3, temp_wav)

        # Stream to Robot (Run in background thread)
        await asyncio.to_thread(_play_audio_blocking, temp_wav, play_animation)

        end_time = time.time()
        print(f"Total processing time: {round(end_time - start_time, 2)} seconds")

        return {"status": "success", "message": "Cozmo successfully spoke."}

    except Exception as e:
        print(f"Error during speech: {e}")
        return {"status": "error", "message": str(e)}