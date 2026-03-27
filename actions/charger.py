import pycozmo
import time
import cv2
import numpy as np
from core.connection import cozmo_manager

latest_image = None


def on_camera_image(cli, image):
    global latest_image
    # Convert to BGR for OpenCV
    latest_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


async def dock_with_charger():
    cli = cozmo_manager.get_robot()
    if not cli:
        return {"error": "Robot not connected"}

    global latest_image
    latest_image = None

    print("Enabling Camera & Debug Window...")
    cli.enable_camera(enable=True, color=True)
    cli.add_handler(pycozmo.event.EvtNewRawCameraImage, on_camera_image)

    cli.move_head(1.0)
    time.sleep(1.5)

    cli.move_head(0.0)
    time.sleep(0.5)

    cli.move_head(-0.5)
    time.sleep(1.5)

    cli.move_head(0.0)
    cli.set_lift_height(pycozmo.robot.MIN_LIFT_HEIGHT.mm)
    time.sleep(1)

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()

    TARGET_MARKER_ID = 0

    print("Starting Radar Spin...")
    cli.drive_wheels(lwheel_speed=5.0, rwheel_speed=-5.0)

    reached_target = False
    max_search_time = time.time() + 18

    try:
        while time.time() < max_search_time:
            if latest_image is not None:
                # Make a copy of the image so we can draw on it without messing up the original
                debug_image = latest_image.copy()

                try:
                    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
                    corners, ids, _ = detector.detectMarkers(debug_image)
                except AttributeError:
                    corners, ids, _ = cv2.aruco.detectMarkers(debug_image, aruco_dict, parameters=parameters)

                # --- DEBUG VISION LOGIC ---
                if ids is not None:
                    # Draw a green square around anything it thinks is a marker
                    cv2.aruco.drawDetectedMarkers(debug_image, corners, ids)

                # Show the live feed on your computer monitor!
                cv2.imshow("Cozmo's Brain ", debug_image)
                cv2.waitKey(1)  # Required for the window to actually update
                # --------------------------

                if ids is not None and TARGET_MARKER_ID in ids:

                    # Find which index in the list belongs to our target ID
                    target_idx = list(ids).index(TARGET_MARKER_ID)
                    c = corners[target_idx][0]

                    # 2. Calculate Center and Width
                    center_x = (c[0][0] + c[1][0] + c[2][0] + c[3][0]) / 4
                    marker_width = abs(c[1][0] - c[0][0])

                    if marker_width > 90:
                        print(f"Close enough! Marker width: {marker_width}px.")
                        cli.stop_all_motors()
                        reached_target = True
                        break

                    # 3. Steering
                    if center_x < 140:
                        cli.drive_wheels(lwheel_speed=-10.0, rwheel_speed=15.0)
                    elif center_x > 180:
                        cli.drive_wheels(lwheel_speed=15.0, rwheel_speed=-10.0)
                    else:
                        cli.drive_wheels(lwheel_speed=35.0, rwheel_speed=35.0)
                else:
                    cli.drive_wheels(lwheel_speed=15.0, rwheel_speed=-15.0)

            time.sleep(0.05)  # Sped up the loop slightly for smoother video

    finally:
        #clean up
        cli.stop_all_motors()
        cli.enable_camera(enable=False)
        cli.del_handler(pycozmo.event.EvtNewRawCameraImage, on_camera_image)
        cv2.destroyAllWindows()

    if not reached_target:
        return {"status": "error", "message": "Could not find the specific ArUco marker."}

    # The Final Docking Turn
    print("Target Reached. Executing 180 turn...")
    cli.drive_wheels(lwheel_speed=-40.0, rwheel_speed=40.0, duration=3.8)
    time.sleep(2.0)
    print("Backing onto charger pins...")
    cli.drive_wheels(lwheel_speed=-40.0, rwheel_speed=-40.0, duration=5.5)
    time.sleep(3.0)

    return {"status": "success", "message": "Visual docking sequence complete."}