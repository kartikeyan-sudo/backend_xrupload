import os
import uuid
import shutil
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .models import UploadResponse, StatusResponse
from .utils import make_unique_filename, allowed_file, safe_filename
from .processing import JOBS, start_job
import aiofiles

logger = logging.getLogger("uvicorn")

app = FastAPI(title="XRCC Video Portal")

# Load .env for local dev; Railway uses env vars
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

NETLIFY_ORIGIN = os.getenv("NETLIFY_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[NETLIFY_ORIGIN, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.abspath("./uploads")
PROCESSED_DIR = os.path.abspath("./processed")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.post("/upload", status_code=202)
async def upload(file: UploadFile = File(...), folder: str = Form(None)):
    filename = safe_filename(file.filename)
    if not allowed_file(filename, file.content_type):
        raise HTTPException(status_code=400, detail="Invalid file type")

    unique = make_unique_filename(filename)
    dest_path = os.path.join(UPLOAD_DIR, unique)
    size = 0
    max_bytes = int(os.getenv('MAX_UPLOAD_MB', '200')) * 1024 * 1024
    async with aiofiles.open(dest_path, 'wb') as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                await out.close()
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
                raise HTTPException(status_code=413, detail="File too large")
            await out.write(chunk)

    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "uploaded", "progress": 5, "message": "uploaded"}

    processed_path = os.path.join(PROCESSED_DIR, f"{job_id}.mp4")
    start_job(job_id, dest_path, processed_path, folder)

    return JSONResponse(status_code=202, content={"job_id": job_id, "filename": filename, "message": "accepted"})

@app.get("/status/{job_id}")
def status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    resp = {
        "job_id": job_id,
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "message": job.get("message"),
    }
    if job.get("status") == "done":
        resp["result_url"] = job.get("result_url")
    if job.get("status") == "error":
        resp["error"] = job.get("error")
    return resp

@app.get("/download/{job_id}")
def download(job_id: str):
    processed_path = os.path.join(PROCESSED_DIR, f"{job_id}.mp4")
    if not os.path.exists(processed_path):
        raise HTTPException(status_code=404, detail="Processed file not found")
    return FileResponse(processed_path, media_type='video/mp4', filename=f"processed_{job_id}.mp4")