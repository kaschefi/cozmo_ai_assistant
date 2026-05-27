from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.hardware.connection import cozmo_manager
from actions.physical.charger import dock_with_charger
from actions.physical.speak import respond
import uvicorn
from schemas import *
from actions.physical.face import FaceLibrary
from actions.physical.timer import run_timer_logic
import asyncio
import threading
from actions.physical.listen import start_listening_loop


def start_console_input_loop(loop: asyncio.AbstractEventLoop):
    """
    Console input loop for physical Cozmo Mode.
    Allows the user to type commands in the terminal when they cannot speak.
    """
    # Local import to prevent circular dependencies
    from core.routing.brain import process_user_intent
    import sys
    import time
    import os

    time.sleep(2.5)  # Let FastAPI and connection messages print first

    GREEN = "\033[92m"
    RESET = "\033[0m"
    GRAY = "\033[90m"
    BLUE = "\033[94m"

    sys.stdout.write(f"\n{BLUE}[Interactive Console Active]{RESET} Type your commands below when you cannot speak:\n")
    sys.stdout.write(f"Type 'quit' or 'exit' to shut down the robot server.\n")
    sys.stdout.flush()

    session_thread_id = f"physical_console_{int(time.time())}"

    while True:
        try:
            command = input(f"\n{GREEN}Type Command: {RESET}").strip()
            
            if not command:
                continue

            if command.lower() in ['quit', 'exit', 'q']:
                print(f"{GRAY}Shutting down Cozmo server...{RESET}")
                os._exit(0)

            print(f"{GRAY}Processing typed command: \"{command}\"...{RESET}")

            # Safely schedule the coroutine in the main loop
            future = asyncio.run_coroutine_threadsafe(
                process_user_intent(command, session_id=session_thread_id),
                loop
            )

            # Wait for response completion
            future.result()
            print(f"{GRAY}Command processed.{RESET}")

        except Exception as e:
            print(f"[Console Error] {e}")
            time.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Cozmo connection...")
    cozmo_manager.robot_mode = True
    cozmo_manager.start()
    # Note: Using get_robot() based on connection.py definition
    app.state.face = FaceLibrary(cozmo_manager.get_robot())

    # Start Cozmo's microphone voice listening loop in a background thread
    print("[lifespan] Starting Cozmo Voice Listening thread...")
    loop = asyncio.get_running_loop()
    listener_thread = threading.Thread(
        target=start_listening_loop,
        args=(loop, app.state.face),
        daemon=True
    )
    listener_thread.start()
    print("[lifespan] Cozmo Voice Listening thread spawned.")

    # Start Cozmo's terminal input console in a background thread
    print("[lifespan] Starting Cozmo Console Input thread...")
    console_thread = threading.Thread(
        target=start_console_input_loop,
        args=(loop,),
        daemon=True
    )
    console_thread.start()
    print("[lifespan] Cozmo Console Input thread spawned.")

    yield
    print("Shutting down... releasing Cozmo.")


app = FastAPI(title="Cozmo AI Bridge", lifespan=lifespan)


@app.post("/actions/dock")
async def handle_dock():
    return await dock_with_charger()


@app.post("/actions/speak")
async def handle_speak(req: SpeakRequest):
    return await respond(req.text, req.play_animation, req.language)


@app.post("/actions/face")
async def trigger_face_act(data: dict):
    face = app.state.face
    act_type = data.get("act")
    params = data.get("params", {})

    if act_type == "timer":
        face.act_timer(params.get("time_str"))
    elif act_type == "weather":
        face.act_weather(params.get("temp"), params.get("condition"))
    elif act_type == "thinking":
        face.act_thinking()
    elif act_type == "reset":
        face.act_reset()

    return {"status": "Face updated"}


@app.post("/actions/timer")
async def handle_timer(req: TimerRequest):
    asyncio.create_task(run_timer_logic(req.seconds, app.state.face))
    return {"status": "success", "message": f"Timer started for {req.seconds} seconds"}


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)