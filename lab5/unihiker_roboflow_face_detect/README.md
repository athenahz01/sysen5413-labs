# UniHiker M10 — Roboflow Cloud Face Detection

Live USB camera feed on the UniHiker M10 with on-demand cloud-based face
detection via the Roboflow Workflows HTTP API.

## Controls

| Button | Action |
|--------|--------|
| **A** | Freeze the current frame, send it to Roboflow for face detection, and draw bounding boxes on the result |
| **B** | Resume the live camera feed |

## Setup

```bash
pip install -r requirements.txt
```

> On a stock UniHiker, `opencv-python` and `unihiker` are typically
> pre-installed. You may only need `pip install requests Pillow`.

## Run

```bash
python main.py
```

## Configuration

Edit the constants at the top of `main.py`:

| Variable | Purpose |
|----------|---------|
| `ROBOFLOW_URL` | Roboflow Workflows endpoint URL |
| `API_KEY` | Your Roboflow API key |
| `JPEG_QUALITY` | JPEG compression quality for the image sent to the API (lower = faster upload, lower quality) |

## How It Works

1. The camera feed is displayed in real time on the UniHiker screen.
2. Pressing **A** freezes the display and sends the current frame (as base64
   JPEG) to the Roboflow workflow endpoint via an HTTP POST request.
3. The response is parsed for bounding-box predictions, which are drawn on the
   frozen image.
4. Pressing **B** clears the detections and resumes the live feed.