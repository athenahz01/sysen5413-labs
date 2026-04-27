#!/usr/bin/env python3
"""
UniHiker M10 Face Detection with Roboflow Cloud API

Press button A to freeze the current frame and run cloud-based face detection.
Press button B to resume the live camera feed.
"""

import argparse
import os
from dotenv import find_dotenv, load_dotenv
import cv2
import base64
import json
import time
import threading
from PIL import Image, ImageDraw
from unihiker import GUI
import requests

# ─── Configuration ───────────────────────────────────────────────────────────

load_dotenv(find_dotenv(usecwd=True))
ROBOFLOW_URL = os.getenv("ROBOFLOW_WORKFLOW_URL")
API_KEY = os.getenv("ROBOFLOW_API_KEY")
if not ROBOFLOW_URL or not API_KEY:
    raise SystemExit("ERROR: ROBOFLOW_WORKFLOW_URL or ROBOFLOW_API_KEY missing in .env")
SCREEN_W, SCREEN_H = 240, 320
BOX_COLOR = "#00FF00"
JPEG_QUALITY = 85

# Capture at 320×240 so after 90° rotation we get exactly 240×320 — no resize
CAP_W, CAP_H = 320, 240

# ─── State machine ──────────────────────────────────────────────────────────

LIVE = "live"
FREEZE_REQ = "freeze_requested"
PROCESSING = "processing"
RESULT = "result"


# ─── Threaded camera reader ─────────────────────────────────────────────────

class CameraReader(threading.Thread):
    """Reads frames in a background thread so USB I/O doesn't block the
    display loop. Frames are rotated (and resized only if needed) here."""

    def __init__(self, cap):
        super().__init__(daemon=True)
        self.cap = cap
        self._frame = None
        self._lock = threading.Lock()
        self._running = True

    def run(self):
        while self._running:
            ret, raw = self.cap.read()
            if not ret:
                continue
            rotated = cv2.rotate(raw, cv2.ROTATE_90_CLOCKWISE)
            h, w = rotated.shape[:2]
            if w != SCREEN_W or h != SCREEN_H:
                rotated = cv2.resize(
                    rotated, (SCREEN_W, SCREEN_H),
                    interpolation=cv2.INTER_NEAREST,
                )
            with self._lock:
                self._frame = rotated

    def grab(self):
        """Return the most recent frame, or None."""
        with self._lock:
            return self._frame

    def stop(self):
        self._running = False


# ─── Frame helpers ───────────────────────────────────────────────────────────

def to_pil(bgr):
    """BGR → PIL RGB via numpy channel reversal (avoids cvtColor overhead)."""
    return Image.fromarray(bgr[:, :, ::-1])


# ─── Roboflow cloud API ─────────────────────────────────────────────────────

def call_roboflow(frame):
    """Encode frame as JPEG base64 and POST to the Roboflow workflow endpoint."""
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    b64 = base64.b64encode(buf).decode("utf-8")

    payload = {
        "api_key": API_KEY,
        "inputs": {
            "image": {"type": "base64", "value": b64},
        },
    }

    resp = requests.post(ROBOFLOW_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    print("Roboflow response (truncated):", json.dumps(data, indent=2)[:800])
    return data


def extract_predictions(data):
    """Walk the JSON tree and collect dicts that look like bounding-box predictions."""
    found = []

    def _walk(obj):
        if isinstance(obj, dict):
            if all(k in obj for k in ("x", "y", "width", "height")):
                found.append(obj)
            else:
                for v in obj.values():
                    _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(data)
    return found


def draw_boxes(frame, predictions):
    """Draw bounding boxes on the frame and return (PIL image, count)."""
    img = to_pil(frame)
    draw = ImageDraw.Draw(img)

    for p in predictions:
        cx, cy = p["x"], p["y"]
        w, h = p["width"], p["height"]
        conf = p.get("confidence", 0)
        label = p.get("class", "face")

        x1 = int(cx - w / 2)
        y1 = int(cy - h / 2)
        x2 = int(cx + w / 2)
        y2 = int(cy + h / 2)

        draw.rectangle([x1, y1, x2, y2], outline=BOX_COLOR, width=2)
        tag = f"{label} {conf:.0%}"
        draw.text((x1 + 2, max(0, y1 - 13)), tag, fill=BOX_COLOR)

    return img, len(predictions)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UniHiker face detection with Roboflow Cloud API"
    )
    parser.add_argument(
        "--confidence", "-c",
        type=float,
        default=0.75,
        help="Minimum confidence threshold (0–1) for detections (default: 0.75)",
    )
    args = parser.parse_args()
    confidence_threshold = args.confidence

    gui = GUI()
    cap = cv2.VideoCapture(0)

    # MJPG transfers compressed frames over USB — huge win on slow ARM SoCs
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    # Match capture to screen dimensions (post-rotation) to skip resize
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_H)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("Cannot open USB camera.")
        return

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc_raw = int(cap.get(cv2.CAP_PROP_FOURCC))
    fourcc_str = "".join(chr((fourcc_raw >> 8 * i) & 0xFF) for i in range(4))
    print(f"Camera: {actual_w}x{actual_h} codec={fourcc_str}")

    reader = CameraReader(cap)
    reader.start()

    bg = gui.draw_image(image="", x=0, y=0)
    gui.fill_rect(x=0, y=SCREEN_H - 26, w=SCREEN_W, h=26, color="#000000")
    info = gui.draw_text(
        text="LIVE | A: Detect  B: Reset",
        x=SCREEN_W // 2, y=SCREEN_H - 13,
        font_size=10, color=BOX_COLOR, origin="center",
    )

    state = LIVE
    current_frame = None
    pending_result = None
    lock = threading.Lock()

    # FPS — averaged over 0.5 s windows instead of per-frame jitter
    fps_count = 0
    fps_timer = time.monotonic()
    displayed_fps = 0.0

    def on_a():
        nonlocal state
        with lock:
            if state == LIVE:
                state = FREEZE_REQ

    def on_b():
        nonlocal state
        with lock:
            state = LIVE

    gui.on_a_click(on_a)
    gui.on_b_click(on_b)

    def _detect_worker(snapshot):
        """Background thread: call Roboflow and package the result."""
        nonlocal state, pending_result
        try:
            data = call_roboflow(snapshot)
            preds = extract_predictions(data)
            preds = [p for p in preds if p.get("confidence", 0) >= confidence_threshold]
            img, n = draw_boxes(snapshot, preds)
            if n > 0:
                msg = f"Found {n} face{'s' if n != 1 else ''} | B: Reset"
                color = BOX_COLOR
            else:
                msg = "No faces found | B: Reset"
                color = "#FF8800"
            with lock:
                if state == PROCESSING:
                    pending_result = (img, msg, color)
                    state = RESULT
        except Exception as e:
            print(f"Detection error: {e}")
            with lock:
                if state == PROCESSING:
                    pending_result = (None, "Error | B: Reset", "#FF4444")
                    state = RESULT

    prev = None

    try:
        while True:
            with lock:
                cur = state

            changed = cur != prev
            prev = cur

            if cur == LIVE:
                if changed:
                    info.config(text="LIVE | A: Detect  B: Reset", color=BOX_COLOR)

                frame = reader.grab()
                if frame is None:
                    time.sleep(0.002)
                    continue

                current_frame = frame
                bg.config(image=to_pil(frame))

                fps_count += 1
                now = time.monotonic()
                elapsed = now - fps_timer
                if elapsed >= 0.5:
                    displayed_fps = fps_count / elapsed
                    fps_count = 0
                    fps_timer = now
                    info.config(
                        text=f"LIVE {displayed_fps:.1f} FPS | A: Detect  B: Reset",
                        color=BOX_COLOR,
                    )

            elif cur == FREEZE_REQ:
                snapshot = (
                    current_frame.copy() if current_frame is not None else None
                )
                with lock:
                    state = PROCESSING
                    prev = PROCESSING

                if snapshot is None:
                    with lock:
                        state = LIVE
                    continue

                bg.config(image=to_pil(snapshot))
                info.config(text="Detecting... please wait", color="#FFFF00")
                threading.Thread(
                    target=_detect_worker, args=(snapshot,), daemon=True
                ).start()

            elif cur == RESULT and changed:
                with lock:
                    result = pending_result
                    pending_result = None
                if result:
                    pil_img, msg, color = result
                    if pil_img is not None:
                        bg.config(image=pil_img)
                    info.config(text=msg, color=color)

            time.sleep(0.005)

    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()
        cap.release()


if __name__ == "__main__":
    main()