# backend/core/routing/encoder.py
import threading
from semantic_router.encoders import FastEmbedEncoder

_encoder_instance = None
_encoder_lock = threading.Lock()

def get_shared_encoder() -> FastEmbedEncoder:
    """
    Returns a thread-safe global singleton instance of FastEmbedEncoder.
    Lazy-loads the model weights on first access to keep module imports instantaneous.
    """
    global _encoder_instance
    if _encoder_instance is None:
        with _encoder_lock:
            if _encoder_instance is None:
                print("[Encoder] Lazy-loading shared FastEmbedEncoder (BAAI/bge-small-en-v1.5)...")
                _encoder_instance = FastEmbedEncoder(name="BAAI/bge-small-en-v1.5")
                print("[Encoder] Shared FastEmbedEncoder initialized.")
    return _encoder_instance
