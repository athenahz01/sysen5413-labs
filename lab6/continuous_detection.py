#!/usr/bin/env python3
"""
UniHiker M10 continuous local object detection with YOLO26N ONNX.

Runs inference continuously (no button press required) and prints detection FPS.
"""

import argparse
import os
import time

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw
from unihiker import GUI

SCREEN_W, SCREEN_H = 240, 320
CAP_W, CAP_H = 320, 240  # becomes 240x320 after rotation
BOX_COLOR = "#00FF00"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "yolo26n.onnx")
CONFIDENCE_THRESHOLD = 0.5


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


def to_pil(bgr):
    return Image.fromarray(bgr[:, :, ::-1])


def letterbox(image, new_shape, color=(114, 114, 114)):
    h, w = image.shape[:2]
    new_h, new_w = new_shape
    scale = min(new_w / w, new_h / h)

    resized_w = int(round(w * scale))
    resized_h = int(round(h * scale))
    resized = cv2.resize(image, (resized_w, resized_h), interpolation=cv2.INTER_LINEAR)

    pad_w = new_w - resized_w
    pad_h = new_h - resized_h
    left = pad_w // 2
    right = pad_w - left
    top = pad_h // 2
    bottom = pad_h - top

    out = cv2.copyMakeBorder(
        resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
    )
    return out, scale, (left, top)


def preprocess(frame, model_h, model_w):
    letterboxed, scale, (pad_x, pad_y) = letterbox(frame, (model_h, model_w))
    rgb = letterboxed[:, :, ::-1]
    normalized = rgb.astype(np.float32) / 255.0
    chw = np.transpose(normalized, (2, 0, 1))
    tensor = np.expand_dims(chw, axis=0)
    return tensor, scale, pad_x, pad_y


def decode_detections(raw_output, confidence_threshold, scale, pad_x, pad_y, frame_shape):
    h, w = frame_shape[:2]
    arr = np.asarray(raw_output)
    if arr.ndim == 3:
        arr = arr[0]
    if arr.ndim != 2 or arr.shape[1] < 6:
        return []

    detections = []
    for det in arr:
        x1, y1, x2, y2, conf, class_id = det[:6]
        if conf < confidence_threshold:
            continue

        x1 = (float(x1) - pad_x) / scale
        y1 = (float(y1) - pad_y) / scale
        x2 = (float(x2) - pad_x) / scale
        y2 = (float(y2) - pad_y) / scale

        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(0, min(w - 1, x2))
        y2 = max(0, min(h - 1, y2))
        if x2 <= x1 or y2 <= y1:
            continue

        cls_idx = int(class_id)
        label = COCO_CLASSES[cls_idx] if 0 <= cls_idx < len(COCO_CLASSES) else f"class_{cls_idx}"
        detections.append(
            {
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2),
                "confidence": float(conf),
                "label": label,
            }
        )
    return detections


def draw_boxes(frame, detections):
    img = to_pil(frame)
    draw = ImageDraw.Draw(img)
    for det in detections:
        x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
        tag = f'{det["label"]} {det["confidence"]:.0%}'
        draw.rectangle([x1, y1, x2, y2], outline=BOX_COLOR, width=2)
        draw.text((x1 + 2, max(0, y1 - 13)), tag, fill=BOX_COLOR)
    return img, len(detections)


def resolve_model_hw(input_shape):
    if len(input_shape) != 4:
        raise ValueError(f"Unexpected model input shape: {input_shape}")
    h, w = input_shape[2], input_shape[3]
    if isinstance(h, int) and isinstance(w, int):
        return h, w
    return 320, 320


def main():
    parser = argparse.ArgumentParser(
        description="UniHiker continuous object detection with local YOLO26N ONNX"
    )
    parser.add_argument(
        "--confidence",
        "-c",
        type=float,
        default=CONFIDENCE_THRESHOLD,
        help="Minimum confidence threshold (0-1), default 0.5",
    )
    parser.add_argument(
        "--print-interval",
        type=float,
        default=1.0,
        help="Seconds between FPS print updates (default: 1.0)",
    )
    args = parser.parse_args()

    try:
        session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
    except Exception as e:
        print(f"Failed to load ONNX model: {e}")
        print("If you see an IR version mismatch, upgrade onnxruntime:")
        print("  pip install --upgrade onnxruntime")
        return

    input_meta = session.get_inputs()[0]
    input_name = input_meta.name
    try:
        model_h, model_w = resolve_model_hw(input_meta.shape)
    except ValueError as e:
        print(e)
        return
    print(f"Model input: {input_name} shape={input_meta.shape} (HxW={model_h}x{model_w})")

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

    bg = gui.draw_image(image="", x=0, y=0)
    gui.fill_rect(x=0, y=SCREEN_H - 26, w=SCREEN_W, h=26, color="#000000")
    info = gui.draw_text(
        text="Detecting continuously...",
        x=SCREEN_W // 2,
        y=SCREEN_H - 13,
        font_size=10,
        color=BOX_COLOR,
        origin="center",
    )

    det_count_window = 0
    det_timer = time.monotonic()

    try:
        while True:
            ret, raw = cap.read()
            if not ret:
                time.sleep(0.002)
                continue

            frame = cv2.rotate(raw, cv2.ROTATE_90_CLOCKWISE)
            h, w = frame.shape[:2]
            if w != SCREEN_W or h != SCREEN_H:
                frame = cv2.resize(frame, (SCREEN_W, SCREEN_H), interpolation=cv2.INTER_NEAREST)

            input_tensor, scale, pad_x, pad_y = preprocess(frame, model_h, model_w)
            outputs = session.run(None, {input_name: input_tensor})
            detections = decode_detections(
                outputs[0],
                confidence_threshold=args.confidence,
                scale=scale,
                pad_x=pad_x,
                pad_y=pad_y,
                frame_shape=frame.shape,
            )

            pil_img, obj_count = draw_boxes(frame, detections)
            bg.config(image=pil_img)

            det_count_window += 1
            now = time.monotonic()
            elapsed = now - det_timer
            if elapsed >= args.print_interval:
                det_fps = det_count_window / elapsed
                print(f"Detection FPS: {det_fps:.2f} | Objects: {obj_count}")
                info.config(text=f"DET {det_fps:.1f} FPS | objs: {obj_count}", color=BOX_COLOR)
                det_count_window = 0
                det_timer = now

    except KeyboardInterrupt:
        pass
    finally:
        cap.release()


if __name__ == "__main__":
    main()