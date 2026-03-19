import pycozmo
import time
from core.connection import cozmo_manager


async def dock_with_charger():
    cli = cozmo_manager.get_robot()
    if not cli:
        return {"error": "Robot not connected"}

    cli.set_head_angle(0.0)
    cli.set_lift_height(0.0)
    time.sleep(1)

    print("Searching for charger...")
    found_charger = None

    def on_object_appeared(cli, obj):
        nonlocal found_charger
        if obj.object_type == pycozmo.protocol_encoder.ObjectType.Charger:
            found_charger = obj

    cli.add_handler(pycozmo.event.EvtObjectAppeared, on_object_appeared)

    cli.drive_wheels(lwheel_speed=20.0, rwheel_speed=-20.0, duration=4.0)

    timeout = time.time() + 10
    while not found_charger and time.time() < timeout:
        time.sleep(0.1)

    cli.del_handler(pycozmo.event.EvtObjectAppeared, on_object_appeared)

    if not found_charger:
        return {"status": "error", "message": "Charger not in sight."}

    target_pose = found_charger.pose
    cli.go_to_pose(target_pose)

    cli.drive_wheels(lwheel_speed=-30.0, rwheel_speed=-30.0, duration=2.0)

    return {"status": "success", "message": "Docking sequence complete."}