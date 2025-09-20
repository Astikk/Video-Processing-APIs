# Video Overlay API

A FastAPI-based backend to apply **image** and **video overlays** on uploaded videos. Supports configurable overlay positions (`x`, `y`) and uses SQLAlchemy with SQLite (or your choice of database) for storing video metadata.

---

## Features

- Overlay an image onto a video
- Overlay a video onto another video
- Configurable overlay coordinates (`x`, `y`)
- Async API with FastAPI
- SQLAlchemy integration for video metadata

---

## Requirements

- Python 3.10+
- FFmpeg installed and available in PATH
- Virtual environment (recommended)

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/video-overlay-api.git
cd video-overlay-api
```

python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Running the server
uvicorn main:app --reload


