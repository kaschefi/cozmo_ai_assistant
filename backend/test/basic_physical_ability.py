import sys
import time
import threading
import numpy as np
import cv2
from PIL import Image, ImageDraw
import pycozmo

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
# Change these values in code to find your ideal sweet spot for room lighting!
# ==============================================================================
cam_params = {
    "red_gain": 0.87,     # Red Channel Multiplier (Decrease if too red/pink | Increase if too green/cyan)
    "blue_gain": 1.05,    # Blue Channel Multiplier (Decrease if too blue | Increase if too yellow)
    "brightness": -70,    # Brightness Offset (Decrease if image is washed out / too bright)
    "contrast": 1.1,     # Contrast Multiplier (Default: 1.10 | Range: 1.0 - 1.3)
    "gamma": 0.7,       # Gamma Curve (Default: 0.85 | Range: 0.7 - 1.0)
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
    Software Color Balance & Exposure Correction Pipeline:
    1. Adjusts Red/Blue channel gains to eliminate pinkish/reddish color cast.
    2. Modifies contrast & brightness to bring down overexposed highlights.
    3. Applies Gamma Look-Up Table (LUT) to restore rich color vibrancy.
    """
    # 1. Channel Balance Adjustment
    b, g, r = cv2.split(raw_bgr_frame)
    b = cv2.convertScaleAbs(b, alpha=params["blue_gain"])
    r = cv2.convertScaleAbs(r, alpha=params["red_gain"])
    frame_balanced = cv2.merge([b, g, r])

    # 2. Contrast & Brightness Adjustment
    frame_adjusted = cv2.convertScaleAbs(
        frame_balanced, alpha=params["contrast"], beta=params["brightness"]
    )

    # 3. Gamma LUT Lookup Correction
    gamma = max(params["gamma"], 0.1)
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    frame_final = cv2.LUT(frame_adjusted, table)

    return frame_final


def on_camera_image(cli, image):
    """
    Ultra-fast PyCozmo camera callback.
    Executes in < 0.1ms by storing ONLY the latest frame reference.
    Drops old queued frames to guarantee ZERO latency stream playback.
    """
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


def run_continuous_physical_and_sensor_test():
    """
    Continuous zero-latency physical ability & real-time sensor/fall logging test
    with automatic camera exposure & color balance correction.
    """
    global latest_raw_image, new_frame_available, frame_count, cam_params

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print(f"{BLUE}====================================================={RESET}")
    print(f"{BLUE}  PYCOZMO STREAM (COLOR CALIBRATED & ZERO LATENCY)    {RESET}")
    print(f"{BLUE}====================================================={RESET}")
    print(f"{YELLOW}[INFO] Auto Color Balance & Exposure Filter ACTIVE (Red tint & brightness fixed).{RESET}")
    print(f"{YELLOW}[HOTKEYS IN STREAM WINDOW]:{RESET}")
    print(f"{GRAY}  ├─ '+' / '-': Adjust Brightness | 'r' / 'e': Red Gain | 'b' / 'v': Blue Gain{RESET}")
    print(f"{GRAY}  └─ '0': Reset Defaults | 'q': Exit Stream{RESET}\n")

    try:
        # --- STEP 1: CONNECT TO ROBOT WITH RETRIES ---
        print(f"{BLUE}[1/4] Connecting to Cozmo hardware...{RESET}")
        connected = False
        cli = None
        for attempt in range(1, 11):
            try:
                print(f"{BLUE}  └─ Connection attempt {attempt}/10...{RESET}")
                cli = pycozmo.Client()
                cli.start()
                cli.connect()
                cli.wait_for_robot(timeout=10.0)
                connected = True
                print(f"{GREEN}[SUCCESS] Connected to Cozmo!{RESET}\n")
                break
            except Exception as conn_err:
                print(f"{YELLOW}  └─ Attempt {attempt} failed ({conn_err}). Retrying in 2 seconds...{RESET}")
                if cli:
                    try:
                        cli.disconnect()
                        cli.stop()
                    except Exception:
                        pass
                    cli = None
                time.sleep(2.0)

        if not connected or cli is None:
            raise RuntimeError("Could not connect to Cozmo after 10 attempts. Please verify Cozmo is powered on and PC is connected to Cozmo's Wi-Fi network.")

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
        draw.text((10, 4), "MOKA MONITORING", fill=1)
        draw.text((15, 16), "CALIBRATED VIDEO", fill=1)
        cli.display_image(img)
        print(f"{GREEN}[SUCCESS] Screen initialized. Starting calibrated stream loop...{RESET}\n")

        # --- STEP 4: ZERO-LATENCY MAIN LOOP WITH COLOR CORRECTION ---
        print(f"{BLUE}[4/4] Real-Time Calibrated Stream Active:{RESET}")
        print(f"{GRAY}-----------------------------------------------------------------------------{RESET}")

        last_telemetry_print = 0.0

        while True:
            # 1. Process and Render Latest Camera Frame in Main Thread (Zero Latency)
            current_raw_img = None
            with lock:
                if new_frame_available:
                    current_raw_img = latest_raw_image
                    new_frame_available = False

            if current_raw_img is not None:
                frame_count += 1
                raw_bgr = cv2.cvtColor(np.array(current_raw_img), cv2.COLOR_RGB2BGR)

                # Apply Software Color Balance & Exposure Enhancement Pipeline
                frame = enhance_cozmo_frame(raw_bgr, cam_params)

                # Header banner
                cv2.putText(
                    frame,
                    f"PyCozmo Calibrated - Frame: {frame_count}",
                    (10, 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (0, 255, 0),
                    1,
                )

                # Fall Warning Overlay
                if latest_sensor_state["is_falling"]:
                    cv2.rectangle(frame, (0, 0), (frame.shape[1], 35), (0, 0, 255), -1)
                    cv2.putText(
                        frame,
                        "!!! WARNING: COZMO IS FALLING !!!",
                        (5, 22),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (255, 255, 255),
                        2,
                    )
                elif latest_sensor_state["cliff_detected"]:
                    cv2.putText(
                        frame,
                        "CLIFF DETECTED!",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 0, 255),
                        2,
                    )

                # Footer Overlay (Displays current color tuning settings)
                orient_text = f"Orient: {latest_sensor_state['orientation']}"
                tune_text = f"R:{cam_params['red_gain']:.2f} B:{cam_params['blue_gain']:.2f} Br:{cam_params['brightness']}"
                cv2.putText(
                    frame,
                    f"{orient_text} | {tune_text}",
                    (10, frame.shape[0] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.35,
                    (255, 255, 255),
                    1,
                )

                cv2.imshow("PyCozmo Direct Stream", frame)

            # 2. Extract Latest Robot Status & Telemetry
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

            accel = getattr(cli, "accel", None)
            accel_tuple = (accel.x, accel.y, accel.z) if accel else (0.0, 0.0, 0.0)
            latest_sensor_state["accel"] = accel_tuple

            # Safety motor stop if falling or cliff detected
            if is_falling or cliff_detected:
                cli.stop_all_motors()

            # 3. Print Telemetry Status Line (Refreshed at ~10Hz)
            now = time.time()
            if now - last_telemetry_print > 0.1:
                fall_indicator = f"{RED}[FALLING!]{RESET}" if is_falling else f"{GREEN}[OK]{RESET}"
                cliff_indicator = f"{RED}[CLIFF]{RESET}" if cliff_detected else f"{GREEN}[SAFE]{RESET}"
                pickup_indicator = f"{YELLOW}[PICKED UP]{RESET}" if is_picked_up else f"{GREEN}[ON GROUND]{RESET}"
                charger_indicator = f"{MAGENTA}[ON CHARGER]{RESET}" if is_on_charger else f"{GRAY}[BATTERY]{RESET}"

                sys.stdout.write(
                    f"\rLive Telemetry ──> Fall: {fall_indicator} | Cliff: {cliff_indicator} | "
                    f"State: {pickup_indicator} | Power: {charger_indicator} | Orient: {orient_str} | Batt: {batt:.2f}V"
                )
                sys.stdout.flush()
                last_telemetry_print = now

            # 4. Handle Live Hotkeys for On-the-fly Color & Exposure Tuning
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                print(f"\n\n{GRAY}User requested exit via stream window.{RESET}")
                break
            elif key == ord("+") or key == ord("="):
                cam_params["brightness"] = min(cam_params["brightness"] + 5, 50)
            elif key == ord("-") or key == ord("_"):
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
                cam_params["contrast"] = 1.10
                cam_params["gamma"] = 0.85

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[INTERRUPTED] Monitor stopped by user.{RESET}")
    except Exception as e:
        print(f"\n\n{RED}[ERROR] Execution failure: {e}{RESET}")
    finally:
        print(f"\n{BLUE}[SHUTDOWN] Stopping motors and releasing camera stream...{RESET}")
        if cli:
            try:
                cli.stop_all_motors()
                cli.enable_camera(enable=False)
                cli.disconnect()
                cli.stop()
            except Exception:
                pass
        cv2.destroyAllWindows()
        print(f"{GREEN}[SHUTDOWN COMPLETE]{RESET}")


if __name__ == "__main__":
    run_continuous_physical_and_sensor_test()