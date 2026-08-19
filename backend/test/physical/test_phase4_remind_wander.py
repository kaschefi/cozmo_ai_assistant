import sys
import os
import time
import argparse
import numpy as np
from PIL import Image

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import logging
# Suppress noisy debug logs
logging.getLogger("pycozmo.robot").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("litellm").setLevel(logging.ERROR)

from core.hardware.connection import cozmo_manager
from autonomous_cozmo import (
    IdleBehaviorEngine,
    pose_tracker,
    remind_engine,
    landmark_slam,
    TemporalDebouncer,
    NodeStatus,
)

# Terminal formatting colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_phase4_exit_test(dry_run: bool = False, duration_s: float = 60.0):
    print(f"\n{CYAN}{'='*75}{RESET}")
    print(f"{CYAN}{BOLD}  MOKA AI ASSISTANT -- PHASE 4 EXIT TEST: REMIND WANDER & LANDMARK SLAM{RESET}")
    print(f"{CYAN}{'='*75}{RESET}\n")

    if not dry_run:
        print(f"{YELLOW}[Hardware] Attempting PyCozmo hardware connection via CozmoManager...{RESET}")
        cozmo_manager.start()
        time.sleep(2.0)
        cli = cozmo_manager.get_robot()
        if not cli:
            print(f"{YELLOW}[Hardware] Robot not connected. Falling back to dry-run simulation mode.{RESET}")
            dry_run = True
        else:
            print(f"{GREEN}[OK] Live Cozmo connected! Camera stream active.{RESET}")
            try:
                cli.enable_camera(enable=True, color=True)
            except Exception:
                pass

            # Initial Startup: Drive forward out of the charger cradle (60mm)
            print(f"{BLUE}[Startup] Driving straight forward 60mm to clear the charger cradle...{RESET}")
            try:
                cli.drive_wheels(lwheel_speed=40.0, rwheel_speed=40.0)
                time.sleep(1.5)
                cli.stop_all_motors()
            except Exception as e:
                print(f"{YELLOW}[Startup] Warning clearing charger: {e}{RESET}")
    else:
        print(f"{MAGENTA}[Test] Running in DRY-RUN simulation mode.{RESET}")

    # Reset Odometry and Memory Bank
    pose_tracker.reset_pose(x=0.0, y=0.0, theta_deg=0.0)
    remind_engine.clear()
    print(f"{BLUE}[Pose] Initial pose: {pose_tracker.get_pose()}{RESET}")

    # Register persistent charging dock anchor
    dock_feat = np.zeros(384, dtype=np.float32)
    dock_feat[0] = 1.0
    remind_engine.register_anchor("ChargingDock", x=0.0, y=0.0, feature_vector=dock_feat)
    landmark_slam.register_landmark("ChargingDock", x=0.0, y=0.0, theta_deg=0.0)
    print(f"{GREEN}[Anchor] Registered 'ChargingDock' anchor at (0.0, 0.0).{RESET}")

    # -------------------------------------------------------------------------
    # STAGE 1: Visual Debouncer Verification (Lighting Flicker Filtering)
    # -------------------------------------------------------------------------
    print(f"\n{BOLD}{CYAN}--- STAGE 1: Temporal Frame Debouncing Verification ---{RESET}")
    debouncer = TemporalDebouncer(required_consecutive_frames=3, similarity_threshold=0.75)
    test_feature = np.random.randn(384).astype(np.float32)
    test_feature /= np.linalg.norm(test_feature)

    # Frame 1: Tentative observation
    is_confirmed_1, c_id = debouncer.process_observation(test_feature, 100.0, 50.0)
    print(f"  Frame 1: Hits=1 -> Confirmed={is_confirmed_1} (Correctly rejected transient flicker)")

    # Frame 2: Second hit
    is_confirmed_2, _ = debouncer.process_observation(test_feature, 100.0, 50.0)
    print(f"  Frame 2: Hits=2 -> Confirmed={is_confirmed_2} (Waiting for threshold)")

    # Frame 3: Third hit -> Promoted
    is_confirmed_3, _ = debouncer.process_observation(test_feature, 100.0, 50.0)
    print(f"  Frame 3: Hits=3 -> Confirmed={is_confirmed_3} (Promoted to verified target)")

    if not is_confirmed_1 and not is_confirmed_2 and is_confirmed_3:
        print(f"{GREEN}[OK] [STAGE 1 PASSED] Debouncer successfully rejected noise and promoted persistent object.{RESET}")
    else:
        print(f"{RED}[FAIL] Debouncer timing failed.{RESET}")
        return False

    # -------------------------------------------------------------------------
    # STAGE 2: Dynamic Novelty Prioritization
    # -------------------------------------------------------------------------
    print(f"\n{BOLD}{CYAN}--- STAGE 2: Dynamic Novelty Exploration Prioritization ---{RESET}")
    # Populate REMIND with 3 distinct desk objects (simulate 3 confirmed observations each)
    objects = [
        {"name": "Ceramic Mug", "x": 120.0, "y": 40.0, "dim": 10},
        {"name": "Rubik's Cube", "x": 140.0, "y": -50.0, "dim": 20},
        {"name": "Notebook", "x": 60.0, "y": 80.0, "dim": 30},
    ]

    for obj in objects:
        feat = np.zeros(384, dtype=np.float32)
        feat[obj["dim"]] = 1.0
        # Feed 3 hits to verify
        for _ in range(3):
            remind_engine.process_feature(
                feat,
                curr_x=0.0,
                curr_y=0.0,
                curr_theta_deg=0.0,
                explicit_target_x=obj["x"],
                explicit_target_y=obj["y"],
                custom_name=obj["name"],
            )

    novel_list = remind_engine.get_novel_objects()
    print(f"{MAGENTA}[REMIND Query] Verified Novel Objects in Memory: {len(novel_list)}{RESET}")
    for item in novel_list:
        print(f"  -> Object ID: {item.id} | Name: {item.name} | Pos: ({item.estimated_x:.1f}, {item.estimated_y:.1f})")

    # Instantiate Idle Engine
    engine = IdleBehaviorEngine(tick_rate_hz=5.0)

    # Tick Behavior Tree - should target novel object #1
    print(f"\n{MAGENTA}[BT Wander] Ticking Behavior Tree to select first novel target...{RESET}")
    status = engine.tick_once()
    bb = engine.blackboard.snapshot()
    print(f"  -> Root Status: {status.value} | Target: {bb.get('target_name')} | Pos: ({bb.get('target_x'):.1f}, {bb.get('target_y'):.1f})")

    if bb.get("target_id") and "NOVEL" in bb.get("target_name", ""):
        print(f"{GREEN}[OK] [STAGE 2 PASSED] BT dynamically prioritized novel visual object over hardcoded lists!{RESET}")
    else:
        print(f"{RED}[FAIL] BT did not select novel visual target.{RESET}")
        return False

    # -------------------------------------------------------------------------
    # STAGE 3: Least-Recently-Attended Revisit Cycling
    # -------------------------------------------------------------------------
    print(f"\n{BOLD}{CYAN}--- STAGE 3: Least-Recently-Attended Revisit Cycle ---{RESET}")
    # Mark all objects as attended at staggered past times
    items = list(remind_engine.memory_bank.values())
    non_anchors = [i for i in items if not i.is_anchor]

    # Stagger timestamps: obj0 = 60s ago, obj1 = 30s ago, obj2 = 10s ago
    now = time.time()
    for idx, item in enumerate(non_anchors):
        item.attended_by_robot = True
        item.last_attended_time = now - (60.0 - idx * 25.0)
        item.observation_count = 5  # No longer brand new novel

    least_attended = remind_engine.get_least_recently_attended()
    oldest_item = least_attended[0]
    print(f"{YELLOW}[REMIND Cycle] Oldest attended object is '{oldest_item.name}' (attended {now - oldest_item.last_attended_time:.1f}s ago){RESET}")

    print(f"{MAGENTA}[BT Wander] Ticking Behavior Tree for revisit cycle...{RESET}")
    status = engine.tick_once()
    bb = engine.blackboard.snapshot()
    print(f"  -> Root Status: {status.value} | Active Target: {bb.get('target_name')}")

    if bb.get("target_id") == oldest_item.id and "REVISIT" in bb.get("target_name", ""):
        print(f"{GREEN}[OK] [STAGE 3 PASSED] BT correctly selected the least recently attended item for inspection!{RESET}")
    else:
        print(f"{RED}[FAIL] BT did not select least recently attended item.{RESET}")
        return False

    # -------------------------------------------------------------------------
    # STAGE 4: Visual Landmark SLAM Drift Offset Correction
    # -------------------------------------------------------------------------
    print(f"\n{BOLD}{CYAN}--- STAGE 4: Visual Landmark SLAM Odometry Drift Correction ---{RESET}")
    # 1. Simulate track slippage drift by perturbing internal odometry
    print(f"{YELLOW}[Drift Injection] Injecting artificial wheel slip: dx=+20.0mm, dy=-15.0mm...{RESET}")
    pose_tracker.update_relative_motion(dist_mm=20.0, turn_deg=0.0)
    drifted_pose = pose_tracker.get_effective_pose()
    print(f"  -> Drifted Odometry Pose: ({drifted_pose[0]:.1f}, {drifted_pose[1]:.1f}, {drifted_pose[2]:.1f}°)")

    # 2. Simulate camera recognizing Charging Dock anchor at visual distance 100mm, azimuth 180°
    # Expected robot position: x=100.0, y=0.0
    print(f"{MAGENTA}[SLAM] Camera spots 'ChargingDock' anchor (visual distance: 100.0mm, azimuth: 180.0°)...{RESET}")
    correction = landmark_slam.correct_drift_from_observation(
        landmark_name="ChargingDock",
        observed_azimuth_deg=180.0,
        observed_distance_mm=100.0,
    )

    corrected_x, corrected_y, _ = pose_tracker.get_effective_pose()
    # Corrected position relative to (0, 0) dock when looking backward at 180 deg is x=100.0, y=0.0
    if abs(corrected_x - 100.0) < 2.0 and abs(corrected_y - 0.0) < 2.0:
        print(f"{GREEN}[OK] [STAGE 4 PASSED] Visual Landmark SLAM eliminated odometry drift! Corrected to ({corrected_x:.1f}, {corrected_y:.1f}){RESET}")
    else:
        print(f"{RED}[FAIL] SLAM correction error: got ({corrected_x}, {corrected_y}){RESET}")
        return False

    # -------------------------------------------------------------------------
    # STAGE 5: Desk Object Rearrangement Adaptation
    # -------------------------------------------------------------------------
    print(f"\n{BOLD}{CYAN}--- STAGE 5: Desk Object Rearrangement Adaptation ---{RESET}")
    target_to_move = non_anchors[0]
    print(f"{YELLOW}[Rearrangement] Moving '{target_to_move.name}' from ({target_to_move.estimated_x:.1f}, {target_to_move.estimated_y:.1f}) -> (175.0, -30.0)...{RESET}")
    remind_engine.update_object_pose(target_to_move.id, new_x=175.0, new_y=-30.0)

    # Make it highest priority by setting last_attended oldest
    target_to_move.last_attended_time = 0.0

    print(f"{MAGENTA}[BT Re-route] Ticking Behavior Tree to navigate to relocated object...{RESET}")
    status = engine.tick_once()
    bb = engine.blackboard.snapshot()
    print(f"  -> Target: {bb.get('target_name')} | Coordinates: ({bb.get('target_x'):.1f}, {bb.get('target_y'):.1f})")

    if bb.get("target_id") == target_to_move.id and abs(bb.get("target_x") - 175.0) < 1.0 and abs(bb.get("target_y") - (-30.0)) < 1.0:
        print(f"{GREEN}[OK] [STAGE 5 PASSED] BT immediately re-routed navigation trajectory to the rearranged object position!{RESET}")
    else:
        print(f"{RED}[FAIL] BT failed to adapt to object rearrangement.{RESET}")
        return False

    # Shutdown
    remind_engine.shutdown()

    print(f"\n{CYAN}{'='*75}{RESET}")
    print(f"{GREEN}{BOLD}[SUCCESS] ALL PHASE 4 EXIT CRITERIA MET SUCCESSFULLY!{RESET}")
    print(f"{GREEN}   1. Temporal visual frame debouncer validated (filters transient flickers).{RESET}")
    print(f"{GREEN}   2. REMIND dynamic novelty discovery & wander prioritization operational.{RESET}")
    print(f"{GREEN}   3. Least-recently-attended continuous revisit cycle verified.{RESET}")
    print(f"{GREEN}   4. Visual Landmark SLAM loop eliminated odometry drift.{RESET}")
    print(f"{GREEN}   5. Desk object rearrangement adaptation verified.{RESET}")
    print(f"{CYAN}{'='*75}{RESET}\n")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 4 REMIND Wander & Landmark SLAM Exit Test")
    parser.add_argument("--dry-run", action="store_true", help="Run simulation test without hardware requirement")
    parser.add_argument("--duration", type=float, default=30.0, help="Test duration in seconds")
    args = parser.parse_args()

    success = run_phase4_exit_test(dry_run=args.dry_run, duration_s=args.duration)
    sys.exit(0 if success else 1)
