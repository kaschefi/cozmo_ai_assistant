import sys
import time
import threading
import numpy as np
import cv2
from PIL import Image, ImageDraw
import pycozmo

from core.hardware.connection import cozmo_manager
from core.routing.layer1.registry import reflex_registry

# Terminal colors for scannable output log
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
GRAY = "\033[90m"
RESET = "\033[0m"

# Thread-safe image buffer for ZERO-LATENCY frame dropping
lock = threading.Lock()
latest_raw_image = None
new_frame_available = False
frame_count = 0

# ==============================================================================
# CAMERA COLOR & EXPOSURE CALIBRATION SETTINGS
# ==============================================================================
cam_params = {
    "red_gain": 0.87,     # Red Channel Multiplier
    "blue_gain": 1.05,    # Blue Channel Multiplier
    "brightness": -70,    # Brightness Offset
    "contrast": 1.1,      # Contrast Multiplier
    "gamma": 0.7,         # Gamma Curve
}

latest_sensor_state = {
    "is_falling": False,
    "cliff_detected": False,
    "is_picked_up": False,
    "battery_voltage": 0.0,
    "orientation": "UNKNOWN",
    "accel": (0.0, 0.0, 0.0),
    "gyro": (0.0, 0.0, 0.0),
}


def enhance_cozmo_frame(raw_bgr_frame, params=cam_params):
    """
    Software Color Balance & Exposure Correction Pipeline.
    """
    b, g, r = cv2.split(raw_bgr_frame)
    b = cv2.convertScaleAbs(b, alpha=params["blue_gain"])
    r = cv2.convertScaleAbs(r, alpha=params["red_gain"])
    frame_balanced = cv2.merge([b, g, r])

    frame_adjusted = cv2.convertScaleAbs(
        frame_balanced, alpha=params["contrast"], beta=params["brightness"]
    )

    gamma = max(params["gamma"], 0.1)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    frame_final = cv2.LUT(frame_adjusted, table)

    return frame_final


def on_camera_image(cli, image):
    """Ultra-fast PyCozmo camera callback."""
    global latest_raw_image, new_frame_available
    with lock:
        latest_raw_image = image
        new_frame_available = True


def on_falling_change(cli, state: bool):
    """Event handler triggered instantly when Cozmo fall status changes."""
    latest_sensor_state["is_falling"] = state
    if state:
        print(f"\n{RED}[ALERT] FREEFALL DETECTED! Cozmo is falling from a surface!{RESET}")
    else:
        print(f"\n{GREEN}[ALERT] Fall ended. Cozmo has stabilized.{RESET}")


def on_cliff_change(cli, state: bool):
    """Event handler triggered instantly when cliff proximity state changes."""
    latest_sensor_state["cliff_detected"] = state
    if state:
        print(f"\n{RED}[ALERT] CLIFF DETECTED! Cozmo detected edge boundary!{RESET}")
    else:
        print(f"\n{GREEN}[ALERT] Cliff cleared. Surface safe.{RESET}")


def on_pickup_change(cli, state: bool):
    """Event handler triggered instantly when pickup status changes."""
    latest_sensor_state["is_picked_up"] = state
    if state:
        print(f"\n{YELLOW}[ALERT] COZMO PICKED UP! Robot lifted off ground.{RESET}")
    else:
        print(f"\n{GREEN}[ALERT] Cozmo placed back down on ground.{RESET}")


def on_orientation_change(cli, orientation):
    """Event handler triggered instantly when orientation changes."""
    orient_name = orientation.name if hasattr(orientation, "name") else str(orientation)
    latest_sensor_state["orientation"] = orient_name
    print(f"\n{CYAN}[ALERT] ORIENTATION CHANGED: {orient_name}{RESET}")


def on_behavior_safety_event(reason: str):
    """Callback when ReflexSafetyGuard intercepts a dangerous condition."""
    print(f"\n{RED}[REFLEX SAFETY INTERCEPT] Safety guard tripped! Reason: {reason}{RESET}")


def run_continuous_physical_and_sensor_test():
    """
    Continuous physical movement & real-time sensor/fall logging test with:
    - WASD Keyboard driving control (Forward, Backward, Left, Right)
    - Up / Down Arrow keys to move hand (lift) up and down
    - ReflexSafetyGuard protection against cliffs and freefalls
    - Calibrated live camera feed with HUD controls display
    """
    global latest_raw_image, new_frame_available, frame_count, cam_params

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"{BLUE}====================================================={RESET}")
    print(f"{BLUE}  PYCOZMO CONTROLLER (WASD + ARROW KEYS + REFLEX SAFETY){RESET}")
    print(f"{BLUE}====================================================={RESET}")
    print(f"{YELLOW}[CONTROL BINDINGS IN STREAM WINDOW]:{RESET}")
    print(f"{GREEN}  ├─ W / S        : Drive Forward / Backward (80 mm/s){RESET}")
    print(f"{GREEN}  ├─ A / D        : Turn Left / Right in Place (60 deg/s){RESET}")
    print(f"{GREEN}  ├─ UP / DOWN    : Move Hand (Lift) Up / Down{RESET}")
    print(f"{GREEN}  ├─ SPACE / X    : Emergency Stop All Motors{RESET}")
    print(f"{GREEN}  ├─ C            : Clear Reflex Safety Guard Trip{RESET}")
    print(f"{GRAY}  ├─ '+' / '-'    : Adjust Brightness | 'r' / 'e': Red Gain | 'b' / 'v': Blue Gain{RESET}")
    print(f"{GRAY}  └─ '0': Reset Defaults | 'q': Exit Stream{RESET}\n")

    try:
        # --- STEP 1: CONNECT TO ROBOT VIA COZMO MANAGER & SAFETY GUARD ---
        print(f"{BLUE}[1/4] Connecting to Cozmo hardware with Reflex Safety Guard...{RESET}")
        cozmo_manager.robot_mode = True
        cozmo_manager.start()

        cli = None
        for attempt in range(1, 25):
            cli = cozmo_manager.get_robot()
            if cli and cozmo_manager.is_connected:
                print(f"{GREEN}[SUCCESS] Connected to Cozmo hardware!{RESET}\n")
                break
            print(f"{BLUE}  └─ Waiting for Wi-Fi handshake ({attempt}/24)...{RESET}")
            time.sleep(0.5)

        if not cli or not cozmo_manager.is_connected:
            raise RuntimeError(
                "Could not connect to Cozmo. Please verify Cozmo is powered ON and PC Wi-Fi is connected to Cozmo's access point."
            )

        # Retrieve and configure Reflex Safety Guard
        guard = cozmo_manager.get_safety_guard()
        if guard:
            guard.register_event_callback(on_behavior_safety_event)
            print(f"{GREEN}[SUCCESS] Reflex Safety Guard registered and monitoring.{RESET}")

        # --- STEP 2: REGISTER EVENT HANDLERS ---
        print(f"{BLUE}[2/4] Registering sensor & camera handlers...{RESET}")
        cli.add_handler(pycozmo.event.EvtRobotFallingChange, on_falling_change)
        cli.add_handler(pycozmo.event.EvtCliffDetectedChange, on_cliff_change)
        cli.add_handler(pycozmo.event.EvtRobotPickedUpChange, on_pickup_change)
        cli.add_handler(pycozmo.event.EvtRobotOrientationChange, on_orientation_change)
        cli.add_handler(pycozmo.event.EvtNewRawCameraImage, on_camera_image)
        cli.enable_camera(enable=True, color=True)
        print(f"{GREEN}[SUCCESS] All listeners active.{RESET}\n")

        # --- STEP 3: INITIALIZE OLED DISPLAY ---
        print(f"{BLUE}[3/4] Initializing OLED Screen Matrix (128x32)...{RESET}")
        img = Image.new("1", (128, 32), color=0)
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, 127, 31), outline=1, fill=0)
        draw.text((8, 4), "WASD + ARROW MODE", fill=1)
        draw.text((12, 16), "SAFETY ACTIVE", fill=1)
        cli.display_image(img)
        print(f"{GREEN}[SUCCESS] Screen initialized. Starting interactive control loop...{RESET}\n")

        # --- STEP 4: INTERACTIVE CONTROL & CAMERA LOOP ---
        print(f"{BLUE}[4/4] Real-Time Calibrated Stream & Control Active:{RESET}")
        print(f"{GRAY}-----------------------------------------------------------------------------{RESET}")

        last_telemetry_print = 0.0
        last_movement_key_time = 0.0
        is_moving = False
        active_action = "IDLE"

        while True:
            # 1. Process and Render Camera Frame with HUD Overlay
            current_raw_img = None
            with lock:
                if new_frame_available:
                    current_raw_img = latest_raw_image
                    new_frame_available = False

            if current_raw_img is not None:
                frame_count += 1
                raw_bgr = cv2.cvtColor(np.array(current_raw_img), cv2.COLOR_RGB2BGR)
                frame = enhance_cozmo_frame(raw_bgr, cam_params)

                # Top Header Banner
                cv2.putText(
                    frame,
                    f"PyCozmo WASD - Frame: {frame_count}",
                    (10, 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 255, 0),
                    1,
                )

                # Active Action Display
                action_color = (0, 255, 255) if active_action != "IDLE" else (200, 200, 200)
                cv2.putText(
                    frame,
                    f"Action: {active_action}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    action_color,
                    2,
                )

                # Safety Guard Status Overlay
                is_safe = guard.is_safe() if guard else True
                if not is_safe:
                    cv2.rectangle(frame, (0, frame.shape[0] - 45), (frame.shape[1], frame.shape[0]), (0, 0, 255), -1)
                    reason_text = guard.last_event_reason if guard else "TRIPPED"
                    cv2.putText(
                        frame,
                        f"!!! SAFETY TRIPPED: {reason_text} !!!",
                        (10, frame.shape[0] - 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (255, 255, 255),
                        2,
                    )
                    cv2.putText(
                        frame,
                        "Press 'C' to clear safety after placing on safe surface",
                        (10, frame.shape[0] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.35,
                        (255, 255, 255),
                        1,
                    )
                else:
                    # Footer Overlay (Color tuning & Legend)
                    orient_text = f"Orient: {latest_sensor_state['orientation']}"
                    legend_text = "WASD: Drive | UP/DN: Hand | SPACE: Stop"
                    cv2.putText(
                        frame,
                        f"{orient_text} | {legend_text}",
                        (10, frame.shape[0] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.35,
                        (255, 255, 255),
                        1,
                    )

                cv2.imshow("PyCozmo Direct Stream", frame)

            # 2. Extract Robot Telemetry
            status = getattr(cli, "robot_status", 0) or 0
            is_falling = bool(status & pycozmo.robot.RobotStatusFlag.IS_FALLING)
            cliff_detected = bool(status & pycozmo.robot.RobotStatusFlag.CLIFF_DETECTED)
            is_picked_up = bool(status & pycozmo.robot.RobotStatusFlag.IS_PICKED_UP)
            is_on_charger = bool(status & pycozmo.robot.RobotStatusFlag.IS_ON_CHARGER)

            latest_sensor_state["is_falling"] = is_falling
            latest_sensor_state["cliff_detected"] = cliff_detected
            latest_sensor_state["is_picked_up"] = is_picked_up

            batt = float(getattr(cli, "battery_voltage", 0.0) or 0.0)
            latest_sensor_state["battery_voltage"] = batt

            orientation = getattr(cli, "robot_orientation", None)
            orient_str = orientation.name if hasattr(orientation, "name") else str(orientation)
            latest_sensor_state["orientation"] = orient_str

            # Print Telemetry Line (~10Hz)
            now = time.time()
            if now - last_telemetry_print > 0.1:
                fall_indicator = f"{RED}[FALLING!]{RESET}" if is_falling else f"{GREEN}[OK]{RESET}"
                cliff_indicator = f"{RED}[CLIFF]{RESET}" if cliff_detected else f"{GREEN}[SAFE]{RESET}"
                safety_indicator = f"{GREEN}[SAFE]{RESET}" if (guard and guard.is_safe()) else f"{RED}[SAFETY LOCK]{RESET}"
                pickup_indicator = f"{YELLOW}[PICKED UP]{RESET}" if is_picked_up else f"{GREEN}[ON GROUND]{RESET}"
                charger_indicator = f"{MAGENTA}[ON CHARGER]{RESET}" if is_on_charger else f"{GRAY}[BATTERY]{RESET}"

                sys.stdout.write(
                    f"\rTelemetry ──> Safety: {safety_indicator} | Fall: {fall_indicator} | Cliff: {cliff_indicator} | "
                    f"State: {pickup_indicator} | Action: {CYAN}{active_action:<12}{RESET} | Batt: {batt:.2f}V"
                )
                sys.stdout.flush()
                last_telemetry_print = now

            # 3. Capture Keyboard Inputs via cv2.waitKeyEx(1)
            key_ex = cv2.waitKeyEx(1)
            key = key_ex & 0xFF if key_ex != -1 else -1

            is_safe_to_move = guard.is_safe() if guard else True

            # Process WASD & Arrow Keys
            if key_ex != -1:
                # --- EXIT ---
                if key == ord("q"):
                    print(f"\n\n{GRAY}User requested exit via stream window.{RESET}")
                    break

                # --- CLEAR SAFETY GUARD ---
                elif key in (ord("c"), ord("C")):
                    if guard:
                        guard.clear_safety()
                        print(f"\n{GREEN}[SAFETY RESET] Reflex safety guard cleared by user.{RESET}")
                        active_action = "SAFETY CLEARED"

                # --- EMERGENCY STOP ---
                elif key in (ord(" "), ord("x"), ord("X")):
                    cli.stop_all_motors()
                    cli.move_lift(0.0)
                    is_moving = False
                    active_action = "STOPPED"

                # --- MOVEMENT COMMANDS (CHECK SAFETY GUARD FIRST) ---
                elif not is_safe_to_move:
                    active_action = "BLOCKED BY SAFETY"
                    is_moving = False

                # W: FORWARD
                elif key in (ord("w"), ord("W")):
                    cli.drive_wheels(lwheel_speed=80.0, rwheel_speed=80.0)
                    last_movement_key_time = time.time()
                    is_moving = True
                    active_action = "FORWARD"

                # S: BACKWARD
                elif key in (ord("s"), ord("S")):
                    cli.drive_wheels(lwheel_speed=-80.0, rwheel_speed=-80.0)
                    last_movement_key_time = time.time()
                    is_moving = True
                    active_action = "BACKWARD"

                # A: TURN LEFT
                elif key in (ord("a"), ord("A")):
                    cli.drive_wheels(lwheel_speed=-60.0, rwheel_speed=60.0)
                    last_movement_key_time = time.time()
                    is_moving = True
                    active_action = "TURN LEFT"

                # D: TURN RIGHT
                elif key in (ord("d"), ord("D")):
                    cli.drive_wheels(lwheel_speed=60.0, rwheel_speed=-60.0)
                    last_movement_key_time = time.time()
                    is_moving = True
                    active_action = "TURN RIGHT"

                # UP ARROW: MOVE HAND (LIFT) UP
                elif key_ex in (2490368, 0x260000) or key == 38 or (key_ex & 0xFFFF) == 38:
                    cli.move_lift(3.0)
                    last_movement_key_time = time.time()
                    is_moving = True
                    active_action = "LIFT UP"

                # DOWN ARROW: MOVE HAND (LIFT) DOWN
                elif key_ex in (2621440, 0x280000) or key == 40 or (key_ex & 0xFFFF) == 40:
                    cli.move_lift(-3.0)
                    last_movement_key_time = time.time()
                    is_moving = True
                    active_action = "LIFT DOWN"

                # CAMERA TUNING HOTKEYS
                elif key in (ord("+"), ord("=")):
                    cam_params["brightness"] = min(cam_params["brightness"] + 5, 50)
                elif key in (ord("-"), ord("_")):
                    cam_params["brightness"] = max(cam_params["brightness"] - 5, -80)
                elif key == ord("r"):
                    cam_params["red_gain"] = round(max(cam_params["red_gain"] - 0.05, 0.2), 2)
                elif key == ord("e"):
                    cam_params["red_gain"] = round(min(cam_params["red_gain"] + 0.05, 1.5), 2)
                elif key == ord("b"):
                    cam_params["blue_gain"] = round(min(cam_params["blue_gain"] + 0.05, 2.5), 2)
                elif key == ord("v"):
                    cam_params["blue_gain"] = round(max(cam_params["blue_gain"] - 0.05, 0.5), 2)
                elif key == ord("0"):
                    cam_params["red_gain"] = 0.85
                    cam_params["blue_gain"] = 1.05
                    cam_params["brightness"] = -15

            # 4. Auto-stop wheels & lift when movement keys are released (> 0.15s)
            if is_moving and (now - last_movement_key_time > 0.15):
                cli.stop_all_motors()
                cli.move_lift(0.0)
                is_moving = False
                active_action = "IDLE"

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[INTERRUPTED] Monitor stopped by user.{RESET}")
    except Exception as e:
        print(f"\n\n{RED}[ERROR] Execution failure: {e}{RESET}")
    finally:
        print(f"\n{BLUE}[SHUTDOWN] Stopping motors and releasing camera stream...{RESET}")
        if cli:
            try:
                cli.stop_all_motors()
                cli.move_lift(0.0)
                cli.enable_camera(enable=False)
            except Exception:
                pass
        cv2.destroyAllWindows()
        print(f"{GREEN}[SHUTDOWN COMPLETE]{RESET}")


if __name__ == "__main__":
    run_continuous_physical_and_sensor_test()