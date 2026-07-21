# Lynce Forensics

Lightweight forensic video analysis pipeline for large-scale CCTV footage.

Lynce was built to solve a very specific problem: reviewing hundreds of hours of surveillance footage on hardware that doesn't have a GPU. Instead of running an object detector over every frame, it first discards most of the video using a cheap motion analysis stage and only runs AI where it's actually needed.

The result is a practical pipeline capable of processing an entire week of recordings from dozens of cameras in under an hour on a standard Intel i3 CPU.

> Developed as a pilot project for a research facility in Cuba.

---

## Features

- Motion-first pipeline that avoids unnecessary AI inference.
- CPU-only execution (no GPU required).
- YOLOv8n inference through ONNX Runtime.
- Automatic fallback to PyTorch when needed.
- Optional Region of Interest (ROI) support.
- Automatic event clipping using FFmpeg.
- CSV report with timestamps and metadata.
- Desktop GUI built with PySide6.
- Headless CLI version.
- Docker support.

---

## How it works

Instead of processing every frame with YOLO, Lynce splits the analysis into two independent stages.

```
Input Video
     │
     ▼
Motion Detection
(Frame Difference)
     │
     ├── No movement → Discard
     │
     ▼
Candidate Segments
     │
     ▼
YOLOv8n (Person Detection)
     │
     ▼
Confirmed Events
     │
     ├── Video Clips
     └── CSV Report
```

### Phase 1 — Motion Detection

The first stage analyzes a reduced number of frames using frame differencing and contour detection.

Its only purpose is answering a simple question:

> *"Did something move here?"*

If the answer is **no**, the segment is discarded immediately.

Since this step is extremely inexpensive, it removes more than 90% of the footage without running any neural network.

---

### Phase 2 — Person Verification

Only the remaining candidate segments are analyzed with YOLOv8n.

Inference runs on CPU using ONNX Runtime whenever possible, reducing execution time while keeping deployment simple.

False positives caused by shadows, illumination changes or camera noise are filtered during this stage.

---

## Project Background

This project was created during a pilot for a Cuban research institution.

The facility stored approximately one week of recordings from **32 surveillance cameras**. When a break-in was discovered days later, security personnel had to manually inspect more than **300 hours of footage** looking for the exact moment someone appeared.

The available hardware was modest:

- Intel Core i3
- No dedicated GPU

Rather than searching for a larger model, the solution was to avoid running AI on the entire video.

By combining a lightweight motion detector with selective YOLO verification, the complete dataset could be processed in **less than one hour** on existing hardware.

---

## Example Workflow

```
32 Cameras
      │
      ▼
300+ Hours of Video
      │
      ▼
Motion Filtering
(~90% discarded)
      │
      ▼
YOLO Verification
      │
      ▼
Detected Events
      │
      ├── Video Clips
      └── CSV Metadata
```

---

## Requirements

- Python 3.10+
- FFmpeg
- 4 GB RAM minimum (8 GB recommended)
- Intel i3 or equivalent CPU

A GPU is **not** required.

---

## Installation

### Docker (recommended)

```bash
docker build -t lynce-forensics .

docker run --rm \
  -v /path/to/videos:/app/videos \
  -v /path/to/output:/app/output \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/models:/app/models \
  lynce-forensics
```

The first execution downloads the YOLOv8n weights automatically.

---

### Local installation

```bash
python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

python main.py
```

---

## Command Line

```bash
python -m src.cli \
    --input /path/to/videos \
    --output /path/to/output \
    --config config.yaml
```

---

## Configuration

The main parameters are defined in `config.yaml`.

| Parameter | Description |
|-----------|-------------|
| `confidence_threshold` | Minimum YOLO confidence |
| `motion_analysis_fps` | FPS used during motion analysis |
| `motion_min_area` | Minimum contour area |
| `roi` | Region of interest |
| `clip_padding_before` | Seconds added before each event |
| `clip_padding_after` | Seconds added after each event |

---

## Output

For every confirmed event, Lynce generates:

- A trimmed video clip.
- Timestamp information.
- Source video reference.
- Event duration.
- CSV report with metadata.

---

## Tech Stack

- Python
- OpenCV
- Ultralytics YOLOv8
- ONNX Runtime
- PySide6
- FFmpeg
- Docker

---

## Repository Structure

```
.
├── src/
├── models/
├── output/
├── config.yaml
├── main.py
├── requirements.txt
└── Dockerfile
```

---

## License

This project is released under the MIT License.