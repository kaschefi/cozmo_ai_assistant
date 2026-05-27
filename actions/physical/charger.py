import pycozmo
import time
import cv2
import numpy as np
from core.hardware.connection import cozmo_manager
from core.routing.registry import reflex_registry

latest_image = None
new_frame_available = False


def on_camera_image(cli, image):
    global latest_image, new_frame_available
    # Convert to BGR for OpenCV
    latest_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    new_frame_available = True

@reflex_registry.reflex("dock_with_charger",[
        "go to sleep",
        "go to your charger",
        "dock yourself",
        "your battery is low",
        "return to base",
        "find the charger",
    ])
async def dock_with_charger():
    cli = cozmo_manager.get_robot()
    if not cli:
        return {"error": "Robot not connected"}

    global latest_image, new_frame_available
    latest_image = None
    new_frame_available = False

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

    # HSV range for target marker of color RGB(204, 255, 51) -> HSV(37, 204, 255)
    # We use a robust range around Hue 37, Saturation 204, and Value 255
    LOWER_YELLOW_GREEN = np.array([15, 30, 80])
    UPPER_YELLOW_GREEN = np.array([60, 255, 255])
    
    # Minimum area in pixels to filter out noise
    MIN_CONTOUR_AREA = 150

    print("Starting Radar Spin...")
    cli.drive_wheels(lwheel_speed=5.0, rwheel_speed=-5.0)

    reached_target = False
    max_search_time = time.time() + 18

    try:
        while time.time() < max_search_time:
            if new_frame_available and latest_image is not None:
                new_frame_available = False
                # Make a copy of the image so we can draw on it without messing up the original
                debug_image = latest_image.copy()

                # Convert to HSV color space
                hsv = cv2.cvtColor(debug_image, cv2.COLOR_BGR2HSV)

                # Threshold the image to get only yellow-green color
                mask = cv2.inRange(hsv, LOWER_YELLOW_GREEN, UPPER_YELLOW_GREEN)

                # Clean up noise with morphological opening and closing
                kernel = np.ones((3, 3), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                # Find contours in the mask
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                # Find the largest contour
                largest_contour = None
                max_area = 0
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area > max_area:
                        max_area = area
                        largest_contour = cnt

                marker_found = False
                center_x = 0
                marker_width = 0

                if largest_contour is not None and max_area >= MIN_CONTOUR_AREA:
                    marker_found = True
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    marker_width = w
                    center_x = x + w / 2.0
                    center_y = y + h / 2.0

                    # --- DEBUG VISION LOGIC ---
                    # Draw a green bounding rectangle around the detected marker
                    cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    # Draw the center point in red
                    cv2.circle(debug_image, (int(center_x), int(center_y)), 5, (0, 0, 255), -1)
                    # Add descriptive text showing width and area
                    cv2.putText(debug_image, f"W: {w}px, Area: {int(max_area)}", (x, max(y - 10, 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

                # Show the live feed on your computer monitor!
                cv2.imshow("Cozmo's Brain ", debug_image)
                cv2.waitKey(1)  # Required for the window to actually update
                # --------------------------

                if marker_found:
                    if marker_width > 50:
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
                        # Lower speed (15.0) to prevent motion blur and keep the green marker in focus
                        cli.drive_wheels(lwheel_speed=15.0, rwheel_speed=15.0)
                else:
                    # Slow, smooth spin (8.0) to search without motion blur
                    cli.drive_wheels(lwheel_speed=8.0, rwheel_speed=-8.0)

            time.sleep(0.01)  # Minimal sleep to keep the loop highly responsive

    finally:
        #clean up
        cli.stop_all_motors()
        cli.enable_camera(enable=False)
        cli.del_handler(pycozmo.event.EvtNewRawCameraImage, on_camera_image)
        cv2.destroyAllWindows()

    if not reached_target:
        return {"status": "error", "message": "Could not find the color marker for the charger."}

    # The Final Docking Turn
    print("Target Reached. Executing 180 turn...")
    cli.drive_wheels(lwheel_speed=-38.0, rwheel_speed=38.0, duration=3.8)
    time.sleep(2.0)
    print("Backing onto charger pins...")
    cli.drive_wheels(lwheel_speed=-40.0, rwheel_speed=-40.0, duration=5.0)
    time.sleep(3.0)

    return {"status": "success", "message": "Visual docking sequence complete."}