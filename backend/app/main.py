import os
import shutil
import uuid
import tempfile
import asyncio
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .processing import process_video
from .cloudinary_utils import configure_cloudinary, upload_video_to_cloudinary

app = FastAPI(title="Motion Detection Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://zesty-kataifi-db2538.netlify.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory structures (note: for production use persistent storage)
jobs: dict = {}
queue: asyncio.Queue = asyncio.Queue()

# TODOs:
# - Add Server-Sent Events (SSE) or WebSockets to stream progress updates to the frontend in real-time.
# - Add authentication/authorization for uploads and result access.
# - Persist jobs to a database for reliability across restarts.
# - Extract thumbnails and detailed motion metadata (timestamps, bounding boxes) for analytics.
# - Add usage dashboard and rate-limiting.


def allowed_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in settings.ALLOWED_EXT


@app.on_event("startup")
async def startup_event():
    # Configure cloudinary, if credentials exist
    configure_cloudinary()
    # Start background worker
    app.state.worker_task = asyncio.create_task(worker())


@app.on_event("shutdown")
async def shutdown_event():
    app.state.worker_task.cancel()


async def worker():
    # Background worker consumes queue and processes videos sequentially
    while True:
        job_id = await queue.get()
        job = jobs.get(job_id)
        if not job:
            queue.task_done()
            continue
        job["status"] = "processing"
        try:
            input_path = job["input_path"]
            tmp_out = os.path.join(tempfile.gettempdir(), f"processed_{job_id}.mp4")

            def progress_cb(fraction, message=""):
                job["progress"] = float(fraction)
                job["message"] = message

            meta = process_video(input_path, tmp_out, update_progress=progress_cb)
            job["progress"] = 0.9

            # Upload to Cloudinary if configured
            uploaded = None
            try:
                uploaded = upload_video_to_cloudinary(tmp_out, folder=job.get("folder"))
            except Exception as e:
                job["status"] = "failed"
                job["message"] = f"Upload failed: {e}"
                queue.task_done()
                continue

            job["status"] = "completed"
            job["result_url"] = uploaded.get("secure_url") or uploaded.get("url")
            job["output_path"] = tmp_out
            job["progress"] = 1.0
        except Exception as e:
            job["status"] = "failed"
            job["message"] = str(e)
        finally:
            queue.task_done()


@app.post("/upload")
async def upload_video(file: UploadFile = File(...), folder: Optional[str] = Form(None)):
    # Validate
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_MB:
        raise HTTPException(status_code=400, detail=f"File too large ({size_mb:.2f} MB). Max {settings.MAX_UPLOAD_MB} MB")

    job_id = str(uuid.uuid4())
    tmp_in = os.path.join(tempfile.gettempdir(), f"upload_{job_id}_{file.filename}")
    with open(tmp_in, "wb") as f:
        f.write(contents)

    jobs[job_id] = {
        "status": "queued",
        "progress": 0.0,
        "message": "Queued",
        "input_path": tmp_in,
        "folder": folder,
    }

    # put into processing queue
    await queue.put(job_id)

    return JSONResponse({"job_id": job_id, "status": "queued"})


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/download/{job_id}")
async def download_processed(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    path = job.get("output_path")
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Processed file not available")
    return FileResponse(path, media_type="video/mp4", filename=os.path.basename(path))

