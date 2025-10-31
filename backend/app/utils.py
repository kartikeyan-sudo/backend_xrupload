import os
import re
import uuid

ALLOWED_EXTS = {'.mp4', '.mov', '.avi', '.mkv'}
ALLOWED_MIMES = {'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska'}

def safe_filename(filename: str) -> str:
    name = os.path.basename(filename)
    name = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    return name

def make_unique_filename(filename: str) -> str:
    base, ext = os.path.splitext(safe_filename(filename))
    return f"{base}_{uuid.uuid4().hex}{ext}"

def allowed_file(filename: str, content_type: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    if ext in ALLOWED_EXTS and content_type in ALLOWED_MIMES:
        return True
    return False