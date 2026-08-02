import time
import asyncio
from core.hardware.connection import cozmo_manager
from core.routing.layer1.registry import reflex_registry
from actions.physical.movement import move_forward, stop_movement


def on_behavior_safety_event(reason: str):
    print(f"\n[BEHAVIOR LAYER NOTIFIED] Event received from hardware: {reason}")


async def run_edge_test():
    cli = cozmo_manager.get_robot()
    if not cli:
        print("Connecting to Cozmo robot (waiting for Wi-Fi handshake)...")
        cozmo_manager.robot_mode = True
        cozmo_manager.start()

        # Wait up to 12 seconds for PyCozmo SDK Wi-Fi connection handshake
        for i in range(24):
            cli = cozmo_manager.get_robot()
            if cli and cozmo_manager.is_connected:
                break
            await asyncio.sleep(0.5)

    if not cli or not cozmo_manager.is_connected:
        print("\n❌ CANNOT RUN EXIT TEST: Robot connection failed.")
        print("   Before running this test:")
        print("   1. Turn ON your physical Cozmo robot.")
        print("   2. Connect your computer Wi-Fi to Cozmo's Wi-Fi access point (e.g. Cozmo_XXXXXX).")
        return

    guard = getattr(reflex_registry, "safety_guard", None) or cozmo_manager.get_safety_guard()
    if not guard:
        print("❌ Error: ReflexSafetyGuard is not registered!")
        return

    # Subscribe behavior layer to safety events
    guard.register_event_callback(on_behavior_safety_event)

    print("\n=======================================================")
    print("        PHASE 1 REFLEX SAFETY EXIT TEST ACTIVE         ")
    print("=======================================================")
    print("1. Driving Cozmo forward toward desk edge at 60 mm/s...")
    cli.drive_wheels(lwheel_speed=60.0, rwheel_speed=60.0)

    # 2. Simulate a severe host-side pipeline hitch (e.g. LLM inference / vision delay)
    print("2. HITCH INJECTED: Main thread freezing for 2 seconds (simulating 2000ms AI freeze)...")
    time.sleep(2.0)

    # 3. Verify that the hardware-level reflex saved the robot independently
    if not guard.is_safe():
        print(f"\n✅ SUCCESS: Reflex thread caught '{guard.last_event_reason}'!")
        print("   Cozmo automatically braked and backed away while the main thread was frozen.")
    else:
        print("\n❌ FAILURE: Safety guard did not trip! Stopping motors.")
        cli.stop_all_motors()

    # Reset
    try:
        input("\nPress Enter to reset safety guard...")
    except (EOFError, KeyboardInterrupt):
        pass
    guard.clear_safety()
    print("Safety guard reset. Ready for next run.")


if __name__ == "__main__":
    asyncio.run(run_edge_test())