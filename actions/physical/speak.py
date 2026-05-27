import pycozmo
import time
import os
import asyncio
import requests
import uuid
import edge_tts
import re
import io
from pydub import AudioSegment
from core.hardware.connection import cozmo_manager
from deep_translator import GoogleTranslator

# Global in-memory cache for translations to bypass slow network requests
translation_cache = {}

def is_persian(text: str) -> bool:
    """Detects if a string contains Persian/Arabic characters."""
    return bool(re.search(r'[\u0600-\u06FF]', text))

def translate_to_persian_with_ai(english_text: str) -> str:
    # 1. Skip if already Persian
    if is_persian(english_text):
        return english_text

    # 2. Check translation cache
    cache_key = f"ai_{english_text}"
    if cache_key in translation_cache:
        print(f"Using cached AI translation: '{translation_cache[cache_key]}'")
        return translation_cache[cache_key]

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
        translation_cache[cache_key] = persian_text
        return persian_text
    except Exception as e:
        print(f"Translation failed: {e}")
        return english_text

def translate_to_persian_with_google(english_text: str) -> str:
    # 1. Skip if already Persian
    if is_persian(english_text):
        print(f"Text is already Persian, skipping translation: '{english_text}'")
        return english_text

    # 2. Check translation cache
    cache_key = f"google_{english_text}"
    if cache_key in translation_cache:
        print(f"Using cached Google translation: '{translation_cache[cache_key]}'")
        return translation_cache[cache_key]

    print(f"Translating to Persian using Google Translate: '{english_text}'")
    try:
        persian_text = GoogleTranslator(source='en', target='fa').translate(english_text)
        print(f"Translation result: {persian_text}")
        translation_cache[cache_key] = persian_text
        return persian_text
    except Exception as e:
        print(f"Translation failed: {e}")
        return english_text


def convert_to_cozmo_format(mp3_bytes: bytes, temp_wav: str):
    """
    Converts MP3 audio bytes in memory directly to a 22kHz mono WAV file on disk.
    Avoids temporary MP3 file writes and shaves latency down.
    """
    print("Converting MP3 bytes to 22kHz WAV...")
    
    # Load MP3 straight from a RAM memory buffer
    audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")

    # Shave silence prepending down from 500ms to 150ms.
    # 150ms is more than enough to stabilize PyCozmo buffers while saving 350ms of lag!
    silence = AudioSegment.silent(duration=150)
    audio = silence + audio

    audio = audio.set_frame_rate(22050).set_channels(1).set_sample_width(2)
    audio.export(temp_wav, format="wav")


def _play_audio_blocking(wav_file: str, play_animation: bool, text: str = None):
    cli = cozmo_manager.get_robot()
    if not cli:
        if text:
            print(f"Robot not connected. Cozmo would say: \"{text}\"")
        return

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

        # 1. Smart Language Translation & Skip Check
        if language == "fa":
            # If the source text is already Farsi, bypass translation network calls completely!
            if is_persian(text):
                text_to_speak = text
                print(f"[Speak Optimization] Bypassed Google Translate (already Persian): \"{text}\"")
            else:
                text_to_speak = await asyncio.to_thread(translate_to_persian_with_google, text)
            voice = "fa-IR-FaridNeural"
        else:
            text_to_speak = text
            voice = "en-US-ChristopherNeural"

        # Unique session ID for safe file cleanup
        file_id = str(uuid.uuid4())[:8]
        temp_wav = f"speech_{file_id}.wav"

        # 2. In-Memory MP3 Speech Generation
        print("[Speak Optimization] Generating Edge-TTS audio directly to memory...")
        communicate = edge_tts.Communicate(text_to_speak, voice)
        
        mp3_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_data.extend(chunk["data"])
        mp3_bytes = bytes(mp3_data)

        # 3. Transcode MP3 Bytes straight to WAV on disk (No temporary MP3 file on disk!)
        await asyncio.to_thread(convert_to_cozmo_format, mp3_bytes, temp_wav)

        # 4. Stream final WAV to Cozmo in a background thread
        await asyncio.to_thread(_play_audio_blocking, temp_wav, play_animation, text_to_speak)

        end_time = time.time()
        print(f"[Speak Optimization] Total speech processing time: {round(end_time - start_time, 2)} seconds")

        return {"status": "success", "message": "Cozmo successfully spoke."}

    except Exception as e:
        print(f"Error during speech: {e}")
        return {"status": "error", "message": str(e)}


async def respond(text: str, play_animation: bool = True, language: str = "en"):
    """
    Unified system response coordinator.
    Always prints to the terminal with beautiful styling,
    and speaks via PyCozmo if running in physical robot mode.
    """
    # Print response text directly in blue color with no prefix
    print(f"\n\033[94m{text}\033[0m\n")
    
    # Check if we are in physical robot mode and the client is active
    if cozmo_manager.robot_mode and cozmo_manager.get_robot():
        # Auto-detect language to Persian if it contains Persian/Arabic unicode characters
        lang = "fa" if is_persian(text) else language
        return await speak_text(text, play_animation, lang)
    
    return {"status": "success", "message": "Printed response to terminal."}