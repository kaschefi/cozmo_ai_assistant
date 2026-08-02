"""
Simple continuous Cozmo charging status reader using pycozmo.

Connects to Cozmo and prints battery_voltage, IS_ON_CHARGER, and
IS_CHARGING live, continuously, straight from the RobotState packet.

Setup:
    pip install pycozmo

Usage:
    python cozmo_live_charge_status.py
    (Ctrl+C to stop)
"""

import time
import datetime
import pycozmo
from pycozmo.robot import RobotStatusFlag

state = {"battery_voltage": None, "status": 0}


def on_robot_state(cli, pkt: pycozmo.protocol_encoder.RobotState):
    state["battery_voltage"] = pkt.battery_voltage
    state["status"] = pkt.status


def main():
    print("Connecting to Cozmo...")
    cli = pycozmo.Client()
    cli.start()
    cli.connect()
    cli.wait_for_robot()
    cli.add_handler(pycozmo.protocol_encoder.RobotState, on_robot_state)
    print("Connected. Reading live status (Ctrl+C to stop)...\n")

    try:
        while True:
            time.sleep(1.0)
            v = state["battery_voltage"]
            s = state["status"]
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            if v is None:
                print(f"{ts}  no data yet")
                continue
            on_charger = bool(s & RobotStatusFlag.IS_ON_CHARGER)
            charging = bool(s & RobotStatusFlag.IS_CHARGING)
            print(f"{ts}  Batt: {v:.3f} V  |  ON_CHARGER: {on_charger}  |  IS_CHARGING: {charging}")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        cli.disconnect()
        cli.stop()


if __name__ == "__main__":
    main()