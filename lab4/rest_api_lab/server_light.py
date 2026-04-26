"""
SYSEN 5413 - Lab 4 Part 1.3: REST API Server (Light-Controlled LED)
Athena Huo
A small Flask server that receives a light sensor reading from the
UniHiker and decides whether the device's LED should be on or off.

The Unihiker reads its light sensor, POSTs the value to /light,
the server applies a threshold, and returns the decision in the
HTTP response. This is closed-loop control over a REST API:
sense -> transmit -> decide -> respond -> actuate.
"""

from flask import Flask, request, jsonify
import threading
import time
from datetime import datetime, timezone

app = Flask(__name__)
START_TIME = time.time()

# Threshold for "is it dark?" - tunable based on environment.
# Light sensor returns roughly 0 (dark) - 4095 (very bright).
# Indoor ambient is usually 200-1000. Below 50 is "covered" / very dark.
LIGHT_THRESHOLD = 50

# Simple in-memory log of the last decisions (helpful for debugging).
_log_lock = threading.Lock()
_decision_log = []


@app.route('/light', methods=['POST'])
def light_control():
    """Receive a light reading and return an LED on/off decision."""
    data = request.get_json(silent=True)
    if data is None or 'light' not in data:
        return jsonify(error="Missing 'light' field in JSON body"), 400
    try:
        light_val = int(data['light'])
    except (TypeError, ValueError):
        return jsonify(error="'light' must be an integer"), 400

    # Core decision: dark room -> turn LED on; bright -> turn it off.
    decision = 'on' if light_val < LIGHT_THRESHOLD else 'off'

    # Log the decision so we can see it in the server terminal.
    with _log_lock:
        ts = datetime.now(timezone.utc).isoformat()
        _decision_log.append({'time': ts, 'light': light_val, 'led': decision})
        # Keep only the last 100 entries
        if len(_decision_log) > 100:
            _decision_log.pop(0)

    print(f"[{ts}] light={light_val:>4}  -> LED {decision}")

    return jsonify(led=decision, light=light_val, threshold=LIGHT_THRESHOLD)


@app.route('/status', methods=['GET'])
def status():
    """Health check + summary."""
    return jsonify(
        status='ok',
        uptime_seconds=round(time.time() - START_TIME, 1),
        threshold=LIGHT_THRESHOLD,
        decisions_logged=len(_decision_log),
    )


if __name__ == '__main__':
    print(f"Light-control server starting (threshold={LIGHT_THRESHOLD}).")
    print("POST {'light': <int>} to /light to get an LED decision.")
    # 0.0.0.0 so the Unihiker on the LAN can reach us
    app.run(host='0.0.0.0', port=5000, debug=False)