import cozmo
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core import cozmo_manager
from actions import dock_with_charger
import uvicorn
from schemas import MoveRequest, SpeakRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing Cozmo connection...")
    cozmo_manager.start()

    yield

    print("Shutting down... releasing Cozmo.")

app = FastAPI(title="Cozmo AI Bridge", lifespan=lifespan)


@app.post("/actions/dock")
async def handle_dock():
    return await dock_with_charger()

#@app.post("/actions/move")
#async def move_robot(req: MoveRequest):
#    robot = cozmo_manager.get_robot()
#    await robot.drive_straight(
#        cozmo.util.distance_mm(req.distance),
#        cozmo.util.speed_mmps(req.speed)
#    ).wait_for_completed()
#    return {"status": "moved", "distance": req.distance}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)