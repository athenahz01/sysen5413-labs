"""
REST API server for the IoT course lab.

Runs on a laptop; the UniHiker M10 client connects over Wi-Fi to post
accelerometer data and receive computed orientation. All endpoints return
application/json so clients can parse responses and errors consistently.
"""

import json
import math
import os
import threading
import time
from datetime import datetime, timezone

from flask import Flask, request, jsonify

# ---------------------------------------------------------------------------
# Uptime and log file
# ---------------------------------------------------------------------------
# We record start time at import so GET /status can report uptime_seconds
# as an application-level metric (seconds since the Flask process started).
start_time = time.time()

# Log file lives next to this script so it works regardless of current
# working directory when the server is started.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "sensor_log.txt")

# Thread-safe file access: Flask may handle multiple requests in different
# threads. A Lock ensures only one request at a time appends or reads the
# log file, avoiding corrupted or interleaved writes.
_file_lock = threading.Lock()

app = Flask(__name__)


# ---------------------------------------------------------------------------
# JSON-only error responses
# ---------------------------------------------------------------------------
# REST APIs often use JSON for errors so clients can parse them the same way
# as success responses. We register handlers so 400/404/500 never return
# Flask's default HTML error pages.
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def json_error(e):
    code = getattr(e, "code", 500)
    msg = getattr(e, "description", None) or str(e)
    return jsonify(error=msg), code


# ---------------------------------------------------------------------------
# POST /orientation — compute roll and pitch from accelerometer readings
# ---------------------------------------------------------------------------
# We use POST (not GET) because the client sends a request body (ax, ay, az).
# GET is for idempotent retrieval with no body; POST is for sending data.
@app.route("/orientation", methods=["POST"])
def orientation():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON"), 400

    for key in ("ax", "ay", "az"):
        if key not in data:
            return jsonify(error=f"Missing required field: {key}"), 400
        val = data[key]
        if not isinstance(val, (int, float)):
            return jsonify(error=f"Field '{key}' must be a number"), 400

    ax = float(data["ax"])
    ay = float(data["ay"])
    az = float(data["az"])

    # Standard formulas: roll from ay/az, pitch from -ax and sqrt(ay²+az²).
    # Result in radians; we convert to degrees for readability.
    roll_rad = math.atan2(ay, az)
    pitch_rad = math.atan2(-ax, math.sqrt(ay * ay + az * az))
    roll = math.degrees(roll_rad)
    pitch = math.degrees(pitch_rad)

    return jsonify(roll=roll, pitch=pitch)


# ---------------------------------------------------------------------------
# POST /data — append one JSON record to the log with server timestamp
# ---------------------------------------------------------------------------
# The server adds server_timestamp (ISO 8601) so we have a server-side
# time of receipt; the client can send client_timestamp for when the sample
# was taken. This teaches clock skew and server authority over "when" something
# was recorded.
@app.route("/data", methods=["POST"])
def append_data():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="Request body must be valid JSON"), 400
    if not isinstance(data, dict):
        return jsonify(error="Request body must be a JSON object"), 400

    payload = dict(data)
    payload["server_timestamp"] = datetime.now(timezone.utc).isoformat()

    with _file_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            line_count = sum(1 for _ in f)

    return jsonify(status="ok", rows_saved=line_count)


# ---------------------------------------------------------------------------
# GET /data — return all logged records as a JSON array
# ---------------------------------------------------------------------------
# GET is used because this is idempotent retrieval of resource state: no
# request body, no side effects. Same URL can be called many times with
# the same result (until new data is posted).
@app.route("/data", methods=["GET"])
def get_data():
    if not os.path.isfile(LOG_FILE):
        return jsonify([])

    records = []
    with _file_lock:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip malformed lines so we still return all valid records.
                    pass

    return jsonify(records)


# ---------------------------------------------------------------------------
# GET /status — health and simple metrics
# ---------------------------------------------------------------------------
# Single endpoint for monitoring: is the server running, how long has it been
# up, and how many rows are in the log. We use the same Lock when reading
# the file so we never read while POST /data is writing.
@app.route("/status", methods=["GET"])
def status():
    uptime_seconds = time.time() - start_time
    rows_logged = 0
    if os.path.isfile(LOG_FILE):
        with _file_lock:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                rows_logged = sum(1 for _ in f)

    return jsonify(
        status="running",
        uptime_seconds=round(uptime_seconds, 2),
        rows_logged=rows_logged,
    )


# ---------------------------------------------------------------------------
# Run the server
# ---------------------------------------------------------------------------
# Bind to 0.0.0.0 so the UniHiker (on another machine) can reach this server
# over the network. Binding to 127.0.0.1 would only allow localhost.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)