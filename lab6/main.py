#!/usr/bin/env python3
"""
UniHiker M10 Local Object Detection with YOLO26N ONNX.

Press button A to freeze the current frame and run local detection.
Press button B to resume the live camera feed.
"""

import argparse
import os
import threading
import time

import cv2
import onnxruntime as ort
from unihiker import GUI

from utils import (
    CameraReader,
    decode_detections,
    draw_boxes,
    preprocess,
    resolve_model_hw,
    to_pil,
)

# ─── Configuration ───────────────────────────────────────────────────────────

SCREEN_W, SCREEN_H = 240, 320
CAP_W, CAP_H = 320, 240  # becomes 240x320 after rotation
BOX_COLOR = "#00FF00"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolo26n.onnx")

# Standard COCO class names (80 classes)
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven",
    "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
    "teddy bear", "hair drier", "toothbrush",
]

# ─── State machine ──────────────────────────────────────────────────────────

LIVE = "live"
FREEZE_REQ = "freeze_requested"
PROCESSING = "processing"
RESULT = "result"

def main():
    parser = argparse.ArgumentParser(
        description="UniHiker object detection with local YOLO26N ONNX"
    )
    parser.add_argument(
        "--confidence",
        "-c",
        type=float,
        default=0.5,
        help="Minimum confidence threshold (0-1), default 0.5",
    )
    args = parser.parse_args()
    confidence_threshold = args.confidence

    try:
        session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
    except Exception as e:
        print(f"Failed to load ONNX model: {e}")
        print("If you see an IR version mismatch, upgrade onnxruntime:")
        print("  pip install --upgrade onnxruntime")
        return
    input_meta = session.get_inputs()[0]
    input_name = input_meta.name
    input_shape = input_meta.shape
    try:
        model_h, model_w = resolve_model_hw(input_shape)
    except ValueError as e:
        print(e)
        return
    print(f"Model input: {input_name} shape={input_shape} (HxW={model_h}x{model_w})")

    gui = GUI()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
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

    reader = CameraReader(cap, SCREEN_W, SCREEN_H)
    reader.start()

    bg = gui.draw_image(image="", x=0, y=0)
    gui.fill_rect(x=0, y=SCREEN_H - 26, w=SCREEN_W, h=26, color="#000000")
    info = gui.draw_text(
        text="LIVE | A: Detect  B: Reset",
        x=SCREEN_W // 2,
        y=SCREEN_H - 13,
        font_size=10,
        color=BOX_COLOR,
        origin="center",
    )

    state = LIVE
    current_frame = None
    pending_result = None
    lock = threading.Lock()

    fps_count = 0
    fps_timer = time.monotonic()

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
        nonlocal state, pending_result
        try:
            input_tensor, scale, pad_x, pad_y = preprocess(snapshot, model_h, model_w)
            outputs = session.run(None, {input_name: input_tensor})
            detections = decode_detections(
                outputs[0],
                confidence_threshold=confidence_threshold,
                scale=scale,
                pad_x=pad_x,
                pad_y=pad_y,
                frame_shape=snapshot.shape,
                class_names=COCO_CLASSES,
            )
            img, count = draw_boxes(snapshot, detections, BOX_COLOR)

            if count > 0:
                msg = f"Found {count} object{'s' if count != 1 else ''} | B: Reset"
                color = BOX_COLOR
            else:
                msg = "No objects found | B: Reset"
                color = "#FF8800"

            with lock:
                if state == PROCESSING:
                    pending_result = (img, msg, color)
                    state = RESULT
        except Exception as e:
            print(f"Inference error: {e}")
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
                snapshot = current_frame.copy() if current_frame is not None else None
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