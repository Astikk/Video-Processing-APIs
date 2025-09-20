from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from db.session import engine, Base, get_db
from models.video import Video
import os, shutil, subprocess

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_video_duration(file_path: str) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        return float(result.stdout)
    except Exception:
        return 0.0

async def upload_video(file, db):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # Save uploaded file
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Get file size
    size = os.path.getsize(file_path)
    
    # Get video duration
    duration = get_video_duration(file_path)
    
    # Save metadata in DB
    new_video = Video(filename=file.filename, size=size, duration=duration)
    db.add(new_video)
    db.commit()
    db.refresh(new_video)
    
    return {
        "id": new_video.id,
        "filename": new_video.filename,
        "size": new_video.size,
        "duration": new_video.duration
    }

async def trim_video(video_id, start, end, db):
    # Fetch video record
    print("Yeah -----------------------")
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    input_path = os.path.join(UPLOAD_DIR, video.filename)
    name, ext = os.path.splitext(video.filename)
    trimmed_filename = f"{name}_trimmed{ext}"
    output_path = os.path.join(UPLOAD_DIR, trimmed_filename)
    
    # Run ffmpeg trim command
    subprocess.run([
        "ffmpeg",
        "-i", input_path,
        "-ss", str(start),
        "-to", str(end),
        "-c", "copy",  # copy codec to avoid re-encoding (faster)
        output_path
    ])
    
    # Save trimmed video metadata in DB
    size = os.path.getsize(output_path)
    duration = end - start
    trimmed_video = Video(filename=trimmed_filename, size=size, duration=duration)
    db.add(trimmed_video)
    db.commit()
    db.refresh(trimmed_video)
    
    return {
        "id": trimmed_video.id,
        "filename": trimmed_video.filename,
        "size": trimmed_video.size,
        "duration": trimmed_video.duration
    }

def add_text_overlay(input_path: str, output_path: str, text: str, x: int = 10, y: int = 10, font_size: int = 24, font_color: str = "white"):
    """
    Adds a text overlay to a video using ffmpeg.
    
    Args:
        input_path (str): Path to input video.
        output_path (str): Path to save output video with text.
        text (str): Text to overlay.
        x (int): X position of text.
        y (int): Y position of text.
        font_size (int): Size of the text font.
        font_color (str): Color of the text.
    """

    # ffmpeg drawtext filter
    # Make sure to escape special characters in text if necessary
    drawtext = f"drawtext=text='{text}':x={x}:y={y}:fontsize={font_size}:fontcolor={font_color}"

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", input_path,
                "-vf", drawtext,   # Video filter
                "-codec:a", "copy",  # Copy audio without re-encoding
                output_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print("[FFMPEG LOG]", result.stderr)
        return {"status": "success", "output_path": output_path}
    except subprocess.CalledProcessError as e:
        print("[FFMPEG ERROR]", e.stderr)
        return {"status": "error", "message": "Failed to add text overlay"}

def add_video_overlay(input_path: str, overlay_video_path: str, output_path: str, x: int = 10, y: int = 10):
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i", input_path,
                "-i", overlay_video_path,
                "-filter_complex", f"[1:v]scale=200:200[ov];[0:v][ov]overlay={x}:{y}",
                "-c:a", "copy",
                output_path
            ],
            check=True,          # raise exception if ffmpeg fails
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=False           # important: prevent automatic UTF-8 decoding
        )
    except subprocess.CalledProcessError as e:
        # Optional: print stderr in binary form or decode safely
        print("FFmpeg failed:", e.stderr.decode('utf-8', errors='ignore'))
        raise

def add_image_overlay(input_path: str, image_path: str, output_path: str, x: int = 10, y: int = 10):
    subprocess.run([
        "ffmpeg",
        "-i", input_path,
        "-i", image_path,
        "-filter_complex", f"overlay={x}:{y}",
        "-c:a", "copy",
        output_path
    ])
