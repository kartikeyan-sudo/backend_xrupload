# Motion Detection Backend

This is a FastAPI backend for a motion-detection video processing service.

Key endpoints:

- POST /upload : upload a video file (form field `file`) and optional `folder` form field for Cloudinary.
- GET /status/{job_id} : get job status, progress, and result URL.
- GET /download/{job_id} : stream processed video file (if available).

Environment variables (can be in `.env`):

- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET

Install and run locally (Windows PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Sample curl to upload:

```bash
curl -F "file=@video.mp4" -F "folder=myfolder" http://localhost:8000/upload
```

Notes and TODOs are included in source. SSE/WebSockets, authentication, and improved persistence are left as TODOs.
