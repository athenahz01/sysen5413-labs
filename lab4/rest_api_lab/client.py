"""
REST API client for the IoT course lab.

Runs on the UniHiker M10. Reads the onboard IMU (accelerometer), posts
readings to the laptop server for orientation computation and logging,
and prints results. All HTTP calls are wrapped in try/except so a missing
or unreachable server does not crash the client — we print a warning and
continue the loop so students can see the effect of network failures.
"""

import argparse
import time
from datetime import datetime, timezone

import requests
from pinpong.board import Board
from pinpong.extension.unihiker import *

# ---------------------------------------------------------------------------
# Parse server address
# ---------------------------------------------------------------------------
# Default is localhost so you can test with server and client on the same
# machine. On the lab network, pass the laptop's IP so the UniHiker can
# reach the server over Wi-Fi (e.g. python client.py 192.168.1.42).
parser = argparse.ArgumentParser(description="UniHiker REST API client — post IMU data to laptop server.")
parser.add_argument(
    "server_ip",
    nargs="?",
    default="127.0.0.1",
    help="IP address of the laptop running server.py (default: 127.0.0.1)",
)
args = parser.parse_args()
BASE_URL = f"http://{args.server_ip}:5000"

# ---------------------------------------------------------------------------
# Initialize hardware
# ---------------------------------------------------------------------------
# Board().begin() is required once so the UniHiker M10 sets up the I2C/SPI
# and onboard sensors; without it the accelerometer calls would fail.
Board().begin()

# Count successful samples so we can print a summary on Ctrl+C (graceful
# shutdown and simple telemetry for the lab).
samples_sent = 0

print(f"Client started. Server: {BASE_URL}")
print("Reading IMU every 1 second. Press Ctrl+C to stop.\n")

try:
    while True:
        # Read raw accelerometer values (m/s² or unitless — server math is the same).
        ax = accelerometer.get_x()
        ay = accelerometer.get_y()
        az = accelerometer.get_z()

        # POST /orientation: server computes roll and pitch so the same math
        # is taught in one place and the client stays thin.
        try:
            r = requests.post(
                f"{BASE_URL}/orientation",
                json={"ax": ax, "ay": ay, "az": az},
                timeout=5,
            )
            r.raise_for_status()
            data = r.json()
            print(f"Roll: {data['roll']:.2f}°, Pitch: {data['pitch']:.2f}°")
        except requests.exceptions.ConnectionError:
            print(f"Warning: Could not reach server at {BASE_URL}. Is the server running and reachable?")
            time.sleep(1)
            continue
        except requests.exceptions.RequestException as e:
            print(f"Warning: /orientation request failed: {e}")
            time.sleep(1)
            continue

        # POST /data: we send client_timestamp (when we took the sample) and
        # the server adds server_timestamp (when it received it). That
        # illustrates clock skew and server authority over recorded time.
        try:
            payload = {
                "ax": ax,
                "ay": ay,
                "az": az,
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            r = requests.post(f"{BASE_URL}/data", json=payload, timeout=5)
            r.raise_for_status()
            data = r.json()
            rows = data.get("rows_saved", 0)
            print(f"  Server has {rows} rows saved.\n")
            samples_sent += 1
        except requests.exceptions.ConnectionError:
            print(f"Warning: Could not reach server at {BASE_URL}. Is the server running and reachable?")
        except requests.exceptions.RequestException as e:
            print(f"Warning: /data request failed: {e}")

        time.sleep(1)

except KeyboardInterrupt:
    print(f"\nStopped. Sent {samples_sent} sample(s) to the server.")