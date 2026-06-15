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
    def __init__(self, model_path: str = "kokoro-v1.0.onnx", voices_path: str = "voices-v1.0.bin"):
        """
        Initializes the VoiceSpeaker engine with zero-disk I/O Kokoro ONNX model.
        """
        self.model_path = model_path
        self.voices_path = voices_path
        self.kokoro = None
        self.sample_rate = 24000  # Default for Kokoro v0.19
        self.block_size = int(self.sample_rate * 0.02)  # 20ms chunks (480 samples)

        # Audio Streaming State
        self._audio_queue = queue.Queue()
        self._remainder = np.array([], dtype=np.float32)
        self._actively_speaking = False
        self._interrupt_flag = False
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
                    outdata[filled:filled+take, 0] = chunk[:take]
                    
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

    async def say(self, text: str, voice: str = "am_echo", speed: float = 1.0) -> None:
        """
        Non-Blocking Async Design:
        Offloads generation to background thread which streams frames to our queue.
        Returns almost instantly.
        """
        if not text:
            return

        sanitized_text = self._sanitize_text(text)
        if not sanitized_text:
            return

        # Windows WASAPI workaround: Re-initialize the audio stream if idle.
        # Opening and closing the microphone stream often silently aborts 
        # the background output stream.
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