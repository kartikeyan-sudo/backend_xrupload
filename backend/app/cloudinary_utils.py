import os
import cloudinary
import cloudinary.uploader
from .config import settings


def configure_cloudinary():
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME") or settings.CLOUDINARY_CLOUD_NAME
    api_key = os.getenv("CLOUDINARY_API_KEY") or settings.CLOUDINARY_API_KEY
    api_secret = os.getenv("CLOUDINARY_API_SECRET") or settings.CLOUDINARY_API_SECRET
    if not (cloud_name and api_key and api_secret):
        return False
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    return True


def upload_video_to_cloudinary(path: str, folder: str | None = None) -> dict:
    """Upload a video file to Cloudinary and return upload response dict."""
    opts = {"resource_type": "video"}
    if folder:
        opts["folder"] = folder
    # Use upload_large if file may be big; uploader.upload will work for most cases
    res = cloudinary.uploader.upload(path, **opts)
    return res
