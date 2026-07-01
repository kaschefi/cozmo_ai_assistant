import asyncio
import re
import traceback
import queue
import threading

# Try to import sounddevice natively
try:
    import sounddevice as sd
    import numpy as np

    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("WARNING: sounddevice or numpy is not installed. Audio playback will be disabled.")

# Try to import kokoro_onnx
try:
    from kokoro_onnx import Kokoro

    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    print("WARNING: kokoro_onnx is not installed. VoiceSpeaker will fallback to silent mode.")


class VoiceSpeaker:
    def __init__(self, model_path: str = "kokoro-v1.0.onnx", voices_path: str = "voices-v1.0.bin",
                 volume_multiplier: float = 4.5):
        """
        Initializes the VoiceSpeaker engine with zero-disk I/O Kokoro ONNX model.
        """
        self.model_path = model_path
        self.voices_path = voices_path
        self.volume_multiplier = volume_multiplier  # Digital gain control
        self.kokoro = None
        self.sample_rate = 24000  # Default for Kokoro v0.19
        self.block_size = int(self.sample_rate * 0.02)  # 20ms chunks (480 samples)

        # Audio Streaming State
        self._audio_queue = queue.Queue()
        self._remainder = np.array([], dtype=np.float32)
        self._actively_speaking = False
        self._interrupt_flag = False
        self._paused = False
        self._stream = None

        self._initialize_model()
        self._initialize_stream()

    @property
    def is_playing(self) -> bool:
        """
        Thread-safe property for listen.py to scale VAD dynamically.
        True ONLY when audio frames are actively being pushed to hardware.
        """
        return self._actively_speaking

    def _initialize_model(self):
        """loads the model into memory at boot time."""
        if not KOKORO_AVAILABLE or not AUDIO_AVAILABLE:
            return

        try:
            print("[VoiceSpeaker] Initializing Kokoro TTS engine into memory...")
            # Load the model into memory once at boot time
            self.kokoro = Kokoro(self.model_path, self.voices_path)
            print("[VoiceSpeaker] Kokoro TTS Engine initialized successfully.")
        except Exception as e:
            print(f"[WARNING] VoiceSpeaker failed to initialize Kokoro model: {e}")
            print("[WARNING] Audio generation will be silently skipped to prevent crashing.")
            self.kokoro = None

    def _initialize_stream(self):
        """Initializes the background audio hardware stream."""
        if not AUDIO_AVAILABLE:
            return

        try:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=self._audio_callback
            )
            self._stream.start()
        except Exception as e:
            print(f"[VoiceSpeaker] Error initializing sounddevice stream: {e}")
            self._stream = None

    def _audio_callback(self, outdata, frames, time, status):
        """
        High-priority C-level callback invoked by PortAudio.
        Pulls exactly `frames` amount of float32 samples from our queue.
        """
        if status:
            print(f"[VoiceSpeaker] Audio callback status: {status}")

        try:
            if self._paused:
                outdata[:] = 0.0
                self._actively_speaking = False
                return

            needed = frames
            filled = 0

            # Start with any leftover samples from the previous callback
            if len(self._remainder) > 0:
                take = min(needed, len(self._remainder))
                outdata[:take, 0] = self._remainder[:take]
                self._remainder = self._remainder[take:]
                needed -= take
                filled += take

            # Pull chunks from the queue until we have enough to satisfy `frames`
            while needed > 0:
                try:
                    chunk = self._audio_queue.get_nowait()
                    take = min(needed, len(chunk))
                    outdata[filled:filled + take, 0] = chunk[:take]

                    if take < len(chunk):
                        self._remainder = chunk[take:]

                    needed -= take
                    filled += take
                except queue.Empty:
                    break

            # If we didn't get enough frames, pad the rest of the buffer with pure silence
            if needed > 0:
                outdata[filled:, 0] = 0.0

            # Update state for the microphone VAD crossover
            if filled > 0:
                self._actively_speaking = True
            else:
                self._actively_speaking = False

        except Exception as e:
            print(f"[VoiceSpeaker] Error in audio callback: {e}")
            outdata[:] = 0.0
            self._actively_speaking = False

    def interrupt(self):
        """
        Instantly halts speaking by clearing the queue and explicitly
        aborting the hardware ring buffer to prevent trailing off.
        """
        self._interrupt_flag = True
        self._paused = False

        # 1. Clear the Queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        self._remainder = np.array([], dtype=np.float32)
        self._actively_speaking = False

        # 2. Hard flush the sounddevice hardware buffer
        if self._stream and AUDIO_AVAILABLE:
            try:
                self._stream.abort()  # Instantly drop buffered frames

                # Recreate the stream for the next speech command
                self._stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='float32',
                    callback=self._audio_callback
                )
                self._stream.start()
            except Exception as e:
                print(f"[VoiceSpeaker] Error restarting stream during interrupt: {e}")

        self._interrupt_flag = False

    def pause(self):
        """Non-destructively pauses audio playback."""
        self._paused = True
        self._actively_speaking = False

    def resume(self):
        """Resumes paused audio playback."""
        self._paused = False

    def _sanitize_text(self, text: str) -> str:
        """
        Dynamic Token Sanitization:
        Strips out raw formatting notation like backticks, clean markdown punctuation,
        and edge-case characters to prevent reading aloud code syntax.
        """
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'`[^`]*`', '', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'[*_~#]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _generate_audio_blocking(self, text: str, voice: str, speed: float = 1.0):
        """
        Heavy ONNX matrix math generation pass (Blocking).
        Generates full sentences/phrases to preserve prosody, then chops into 20ms chunks.
        """
        if not self.kokoro or self._interrupt_flag:
            return

        try:
            # Kokoro generates the entire audio chunk in memory
            samples, _ = self.kokoro.create(
                text, voice=voice, speed=speed, lang="en-us"
            )

            if self._interrupt_flag:
                return

            # Apply digital volume multiplier and prevent clipping distortion
            if self.volume_multiplier != 1.0:
                samples = np.clip(samples * self.volume_multiplier, -0.95, 0.95)

            # Chop the resulting float32 array into discrete 20ms frames and enqueue
            total_samples = len(samples)
            for i in range(0, total_samples, self.block_size):
                if self._interrupt_flag:
                    break

                chunk = samples[i:i + self.block_size]
                self._audio_queue.put(chunk)

        except Exception as e:
            print(f"[VoiceSpeaker] Error during ONNX generation: {e}")
            traceback.print_exc()

    def _generate_robot_audio_blocking(self, text: str, voice: str, speed: float = 1.0):
        """
        Generates full sentences/phrases to preserve prosody, resamples to 22050Hz,
        and saves as a mono 16-bit WAV file for physical Cozmo playback.
        """
        if not self.kokoro:
            return

        try:
            # Kokoro generates the entire audio chunk in memory (24000Hz, float32)
            samples, _ = self.kokoro.create(
                text, voice=voice, speed=speed, lang="en-us"
            )

            # Apply digital volume multiplier and prevent clipping distortion
            if self.volume_multiplier != 1.0:
                samples = np.clip(samples * self.volume_multiplier, -0.95, 0.95)

            # Resample from 24000Hz to 22050Hz (using linear interpolation)
            num_in_samples = len(samples)
            num_out_samples = int(num_in_samples * 22050 / 24000)

            original_indices = np.linspace(0, num_in_samples - 1, num_in_samples)
            new_indices = np.linspace(0, num_in_samples - 1, num_out_samples)
            resampled = np.interp(new_indices, original_indices, samples)

            # Convert float32 to 16-bit PCM
            pcm_data = np.clip(resampled * 32767.0, -32768, 32767).astype(np.int16)

            # Save to temporary WAV file using python's built-in wave module
            import wave
            with wave.open("temp_speech.wav", "wb") as wav_file:
                wav_file.setnchannels(1)  # mono
                wav_file.setsampwidth(2)  # 16-bit (2 bytes)
                wav_file.setframerate(22050)  # 22050 Hz
                wav_file.writeframes(pcm_data.tobytes())

        except Exception as e:
            print(f"[VoiceSpeaker] Error generating robot audio: {e}")
            traceback.print_exc()

    async def say(self, text: str, voice: str = "am_echo", speed: float = 1.0) -> None:
        """
        Plays speech response. If Cozmo physical mode is active and the robot is connected,
        it resamples the audio and plays it directly on Cozmo's speaker.
        Otherwise, it falls back to streaming on the PC speaker.
        """
        if not text:
            return

        sanitized_text = self._sanitize_text(text)
        if not sanitized_text:
            return

        # Check if Cozmo robot connection is active
        from core.hardware.connection import cozmo_manager
        import pycozmo
        cli = cozmo_manager.get_robot() if cozmo_manager.robot_mode else None

        if cli:
            # Physical Robot Speech: Generate 22050Hz WAV and play on Cozmo speaker
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._generate_robot_audio_blocking, sanitized_text, voice, speed
            )
            try:
                import os
                wav_path = os.path.abspath("temp_speech.wav")
                # Set Cozmo volume to maximum (65535 is the hardware limit for 16-bit unsigned)
                try:
                    cli.set_volume(65535)
                except Exception as e:
                    print(f"[VoiceSpeaker] Failed to set volume: {e}")
                cli.play_audio(wav_path)
                cli.wait_for(pycozmo.event.EvtAudioCompleted)
            except Exception as e:
                print(f"[VoiceSpeaker] Error playing audio on Cozmo: {e}")
            return

        # PC Speaker Fallback:
        # Windows WASAPI workaround: Re-initialize the audio stream if idle.
        if AUDIO_AVAILABLE and not self._actively_speaking:
            try:
                if self._stream:
                    self._stream.abort()
                    self._stream.close()
            except Exception:
                pass
            self._initialize_stream()

        loop = asyncio.get_running_loop()

        # Thread-Safe Offloading:
        # Offload the heavy ONNX matrix math generation pass to a background thread pool executor
        await loop.run_in_executor(
            None, self._generate_audio_blocking, sanitized_text, voice, speed
        )

        # Safety Guard: If stream or audio is not initialized/available, flush the queue and return
        if not AUDIO_AVAILABLE or not self._stream or not self.kokoro:
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    break
            return

        # Wait for the audio stream to finish playing
        # Sleep briefly to let the callback process the first chunk and flag actively_speaking
        await asyncio.sleep(0.05)
        while self._stream.active and (self._actively_speaking or not self._audio_queue.empty()):
            await asyncio.sleep(0.05)


# Global instance for easy import across the project
speaker = VoiceSpeaker()


# -------------------------------------------------------------------------
# Legacy Adapters (Preserved to prevent breaking other modules)
# -------------------------------------------------------------------------

async def respond(text: str, play_animation: bool = True, language: str = "en"):
    """
    Unified system response coordinator (Updated to use local Kokoro TTS).
    Always prints to the terminal with beautiful styling.
    """
    # Print response text directly in blue color with no prefix
    print(f"\n\033[94m{text}\033[0m\n")

    # Bypass language translation networks to stay offline, route immediately to local Kokoro.
    await speaker.say(text, voice="am_echo")

    return {"status": "success", "message": "Response processed via local VoiceSpeaker."}


async def speak_text(text: str, play_animation: bool = True, language: str = "en"):
    """Legacy wrapper for speak_text"""
    return await respond(text, play_animation, language)