from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status, Form
from sqlalchemy.orm import Session
from celery_app import celery
from celery.result import AsyncResult
from db.session import engine, Base, get_db
from models.video import Video
from pydantic import BaseModel
from uuid import uuid4
import os

from services.video_services import (
    get_video_duration,
    upload_video as upload_video_service,
    trim_video as trim_video_service,
    add_text_overlay,
    add_video_overlay,
    add_image_overlay
)
from tasks import overlay_video_task

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "processed"

class TextOverlayRequest(BaseModel):
    video_id: int
    text: str
    x: int = 10
    y: int = 10
    font_size: int = 24
    font_color: str = "white"

class OverlayImageRequest(BaseModel):
    video_id: int
    x: int = 10
    y: int = 10

# class VideoOverlayRequest(BaseModel):
#     video_id: int
#     x: int = 10
#     y: int = 10

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Video Processing API")


# Utility function to get video duration using ffmpeg
def get_video_duration(file_path: str) -> float:
    return get_video_duration()

# -----------------------------
# Level 1 – Upload & Metadata
# -----------------------------
@app.post("/upload")
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await upload_video_service(file, db)

@app.get("/videos")
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).all()
    return videos

# -----------------------------
# Level 2 – Trim API
# -----------------------------
@app.get("/trim")
async def trim_video(video_id: int, start: int, end: int, db: Session = Depends(get_db)):
    return await trim_video_service(video_id, start, end, db)

@app.post("/overlay/text")
async def overlay_text(request: TextOverlayRequest, db: Session = Depends(get_db)):
    # 1️⃣ Validate request fields manually before DB call
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty."
        )
    if request.x < 0 or request.y < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x and y positions must be non-negative."
        )
    if request.font_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="font_size must be greater than zero."
        )

    # Fetch video from DB
    video = db.query(Video).filter(Video.id == request.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    input_path = os.path.join(UPLOAD_DIR, video.filename)
    name, ext = os.path.splitext(video.filename)
    output_filename = f"{name}_overlay{ext}"
    output_path = os.path.join(UPLOAD_DIR, output_filename)

    # Call utility function

    response = add_text_overlay(
        input_path=input_path,
        output_path=output_path,
        text=request.text,
        x=request.x,
        y=request.y,
        font_size=request.font_size,
        font_color=request.font_color
    )

    if response["status"] == "error":
        raise HTTPException(status_code=500, detail=response["message"])

    # Save new video entry in DB
    size = os.path.getsize(output_path)
    new_video = Video(filename=output_filename, size=size, duration=video.duration)
    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    return {
        "id": new_video.id,
        "filename": new_video.filename,
        "size": new_video.size,
        "duration": new_video.duration
    }

@app.post("/overlay/image")
async def overlay_image(
    video_id: int = Form(...),
    image_file: UploadFile = File(...),
    x: int = Form(10),
    y: int = Form(10),
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return {"error": "Video not found"}

    input_path = os.path.join(UPLOAD_DIR, video.filename)
    output_path = os.path.splitext(input_path)[0] + "_image_overlay.mp4"

    # Save uploaded file temporarily
    temp_image_path = f"temp_{image_file.filename}"
    with open(temp_image_path, "wb") as f:
        f.write(await image_file.read())

    add_image_overlay(input_path, temp_image_path, output_path, x, y)

    # Optionally, remove temp file
    os.remove(temp_image_path)

    return {"message": "Image overlay applied", "output_path": output_path}


@app.post("/overlay/video")
async def overlay_video(
    video_id: int = Form(...),
    x: int = Form(10),
    y: int = Form(10),
    overlay_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return {"error": "Video not found"}

    input_path = os.path.join(UPLOAD_DIR, video.filename)
    overlay_path = os.path.join(UPLOAD_DIR, overlay_file.filename)

    # Save uploaded overlay video
    with open(overlay_path, "wb") as f:
        f.write(await overlay_file.read())

    # output_path = os.path.splitext(input_path)[0] + "_video_overlay.mp4"
    output_filename = f"{uuid4()}_video_overlay.mp4"
    output_path = os.path.join(UPLOAD_DIR, output_filename)

    # Enqueue task
    add_video_overlay(input_path, overlay_path, output_path, x, y)

    return {"message": "Video overlay applied", "output_path": output_path}

    # some issue in here, i will do it later... 

    # overlay_video_task.delay(input_path, overlay_path, output_path, x, y)
    # return {"job_id": job.id}

# @app.post("/overlay/video")
# async def overlay_video_endpoint(
#     video_id: int = Form(...),
#     x: int = Form(10),
#     y: int = Form(10),
#     overlay_file: UploadFile = File(...),
#     db: Session = Depends(get_db)
# ):
#     video = db.query(Video).filter(Video.id == video_id).first()
#     if not video:
#         return {"error": "Video not found"}

#     input_path = os.path.join(UPLOAD_DIR, video.filename)

#     # Save uploaded overlay video with unique name
#     overlay_filename = f"{uuid4()}_{overlay_file.filename}"
#     overlay_path = os.path.join(UPLOAD_DIR, overlay_filename)
#     with open(overlay_path, "wb") as f:
#         f.write(await overlay_file.read())

#     output_filename = f"{uuid4()}_video_overlay.mp4"
#     output_path = os.path.join(OUTPUT_DIR, output_filename)

#     # Enqueue task
#     job = overlay_video_task.delay(input_path, overlay_path, output_path, x, y)

#     return {"job_id": job.id}

@app.get("/status/{job_id}")
def get_status(job_id: str):
    job = AsyncResult(job_id, app=celery)
    return {"job_id": job_id, "status": job.status}
