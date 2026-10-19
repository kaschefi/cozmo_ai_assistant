import asyncio
import time
import json
from typing import Optional, Set
from fastapi import WebSocket

from core.hardware.connection import cozmo_manager
from schemas.chat_history_db import chat_history_db


class VoiceBridge:
    """
    Manages the physical Cozmo voice listener lifecycle, session tracking,
    and real-time event broadcasting between the physical microphone/speaker
    and the web chat interface.
    """
    def __init__(self):
        self.task: Optional[asyncio.Task] = None
        self.is_active: bool = False
        self.current_session_id: str = "web_session"
        self.subscribers: Set[WebSocket] = set()
        self._listener = None
        self.state: str = "IDLE"  # IDLE, INITIALIZING, LISTENING, PROCESSING, SPEAKING

    async def register_subscriber(self, ws: WebSocket, session_id: Optional[str] = None):
        """Registers a WebSocket connection from the frontend and sends initial status."""
        self.subscribers.add(ws)
        if session_id:
            self.current_session_id = session_id
        is_conn = cozmo_manager.is_connected
        err_msg = getattr(cozmo_manager, "last_error", None) if not is_conn else None
        calc_state = self.state if is_conn else ("FAILED" if err_msg else "IDLE")
        await self.send_to_ws(ws, {
            "type": "cozmo_voice_status",
            "is_connected": is_conn,
            "is_connecting": cozmo_manager.is_connecting,
            "is_listening": self.is_active and is_conn,
            "state": calc_state,
            "error": err_msg,
            "session_id": self.current_session_id
        })

    def unregister_subscriber(self, ws: WebSocket):
        """Unregisters a disconnected WebSocket."""
        self.subscribers.discard(ws)

    def set_session_id(self, session_id: str):
        """Updates the active chat session ID so voice messages attach to the current thread."""
        if session_id:
            self.current_session_id = session_id

    async def broadcast(self, payload: dict):
        """Broadcasts a JSON event to all registered WebSocket subscribers."""
        if not self.subscribers:
            return
        dead = []
        msg = json.dumps(payload)
        for ws in list(self.subscribers):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.subscribers.discard(ws)

    async def send_to_ws(self, ws: WebSocket, payload: dict):
        """Sends a JSON event to a specific WebSocket subscriber."""
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            self.subscribers.discard(ws)

    async def _get_or_create_listener(self):
        """Lazily loads the Whisper and Silero VAD models in an executor thread."""
        if self._listener is not None:
            return self._listener
        self.state = "INITIALIZING"
        await self.broadcast({
            "type": "cozmo_voice_status",
            "is_connected": cozmo_manager.is_connected,
            "is_connecting": cozmo_manager.is_connecting,
            "is_listening": self.is_active,
            "state": self.state,
            "session_id": self.current_session_id
        })
        loop = asyncio.get_running_loop()

        def _load():
            from actions.physical.listen import VoiceListener
            return VoiceListener(device="cpu", compute_type="int8")

        self._listener = await loop.run_in_executor(None, _load)
        return self._listener

    async def start(self, session_id: Optional[str] = None):
        """Starts the physical voice listener background task."""
        if session_id:
            self.current_session_id = session_id
        if self.is_active and self.task and not self.task.done():
            return

        self.is_active = True
        self.task = asyncio.create_task(self._listen_loop())
        await self.broadcast({
            "type": "cozmo_voice_status",
            "is_connected": cozmo_manager.is_connected,
            "is_connecting": cozmo_manager.is_connecting,
            "is_listening": True,
            "state": "INITIALIZING",
            "session_id": self.current_session_id
        })

    async def stop(self):
        """Gracefully halts the physical voice listener background task."""
        self.is_active = False
        self.state = "IDLE"
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

        err_msg = getattr(cozmo_manager, "last_error", None) if not cozmo_manager.is_connected else None
        await self.broadcast({
            "type": "cozmo_voice_status",
            "is_connected": cozmo_manager.is_connected,
            "is_connecting": cozmo_manager.is_connecting,
            "is_listening": False,
            "state": "FAILED" if err_msg else "IDLE",
            "error": err_msg,
            "session_id": self.current_session_id
        })

    async def _listen_loop(self):
        """Main listening loop watching for 'Hey Buddy' wake word and streaming to chat."""
        from core.routing.brain import process_user_intent
        try:
            listener = await self._get_or_create_listener()
            print("[VoiceBridge] Ready! Say 'Hey Buddy' followed by your command.")
            self.state = "LISTENING"
            if self.is_active and (cozmo_manager.is_connected or cozmo_manager.is_connecting):
                await self.broadcast({
                    "type": "cozmo_voice_status",
                    "is_connected": cozmo_manager.is_connected,
                    "is_connecting": cozmo_manager.is_connecting,
                    "is_listening": True,
                    "state": "LISTENING" if cozmo_manager.is_connected else "CONNECTING",
                    "error": None,
                    "session_id": self.current_session_id
                })

            require_wake = True
            while self.is_active:
                timeout = 4.0 if not require_wake else None
                try:
                    command = await listener.listen_and_transcribe(require_wake=require_wake, timeout=timeout)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[VoiceBridge] Listen error: {e}")
                    await asyncio.sleep(0.5)
                    continue

                if not self.is_active:
                    break

                if command is None:
                    # Expectant window timed out, revert to requiring wake word
                    require_wake = True
                    self.state = "LISTENING"
                    await self.broadcast({
                        "type": "listener_state",
                        "state": "LISTENING_WAKE_WORD"
                    })
                    continue

                if command:
                    print(f"[VoiceBridge] Heard Command: '{command}'")
                    self.state = "PROCESSING"

                    # 1. Broadcast user voice message to the web chat interface
                    await self.broadcast({
                        "type": "user_voice_message",
                        "session_id": self.current_session_id,
                        "text": command,
                        "timestamp": time.time()
                    })

                    # 2. Persist user message to chat DB
                    chat_history_db.add_message(
                        session_id=self.current_session_id,
                        sender="user",
                        text=command,
                        model_mode="local"
                    )

                    # 3. Process through Unified Brain (with mute=False so Cozmo speaks)
                    self.state = "SPEAKING"
                    await self.broadcast({
                        "type": "listener_state",
                        "state": "SPEAKING"
                    })

                    try:
                        # process_user_intent automatically calls respond(final_answer, mute=False)
                        # which routes directly to Cozmo's speaker because cozmo_manager.robot_mode is True and cli is connected.
                        response_text = await process_user_intent(
                            command,
                            session_id=self.current_session_id,
                            mute=False,
                            provider="local"
                        )
                    except Exception as e:
                        print(f"[VoiceBridge] Cognitive process error: {e}")
                        response_text = f"I ran into an issue processing that: {e}"

                    # 4. Persist AI response to chat DB
                    if response_text:
                        chat_history_db.add_message(
                            session_id=self.current_session_id,
                            sender="moka",
                            text=response_text,
                            model_mode="local"
                        )

                    # 5. Broadcast AI response to the web chat interface
                    await self.broadcast({
                        "type": "agent_voice_response",
                        "session_id": self.current_session_id,
                        "text": response_text,
                        "timestamp": time.time()
                    })

                    # Enter expectant window for follow-up conversation
                    require_wake = False
                    self.state = "LISTENING"
                    await self.broadcast({
                        "type": "listener_state",
                        "state": "EXPECTANT_WINDOW"
                    })

        except asyncio.CancelledError:
            print("[VoiceBridge] Voice listening task cancelled.")
        except Exception as e:
            print(f"[VoiceBridge] Fatal error in voice bridge: {e}")
        finally:
            self.state = "IDLE"
            self.is_active = False


voice_bridge = VoiceBridge()
