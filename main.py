import cozmo
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core import cozmo_manager
from actions import dock_with_charger, speak_text
import uvicorn
from schemas import *
from actions.face import FaceLibrary
from actions.timer import run_timer_logic
import asyncio


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Cozmo connection...")
    cozmo_manager.start()
    app.state.face = FaceLibrary(cozmo_manager.robot)
    yield

    print("Shutting down... releasing Cozmo.")

app = FastAPI(title="Cozmo AI Bridge", lifespan=lifespan)


@app.post("/actions/dock")
async def handle_dock():
    return await dock_with_charger()

@app.post("/actions/speak")
async def handle_speak(req: SpeakRequest):
    return await speak_text(req.text, req.play_animation, req.language)

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

    @app.post("/actions/timer")
    async def handle_timer(req: TimerRequest):
        asyncio.create_task(run_timer_logic(req.seconds, app.state.face))
        return {"status": "success", "message": f"Timer started for {req.seconds} seconds"}

    return {"status": "Face updated"}
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)