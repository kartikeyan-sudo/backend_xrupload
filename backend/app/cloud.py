import os
import logging
from typing import Optional, Dict
import cloudinary
import cloudinary.uploader

logger = logging.getLogger(__name__)

def configure_cloudinary_from_env():
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True,
    )

def upload_video(path: str, folder: Optional[str] = None, public_id: Optional[str] = None) -> Dict:
    configure_cloudinary_from_env()
    opts = {"resource_type": "video"}
    if folder:
        opts["folder"] = folder
    if public_id:
        opts["public_id"] = public_id

    size = os.path.getsize(path)
    try:
        if size > 100 * 1024 * 1024:
            logger.info("Using upload_large for big file %s", path)
            resp = cloudinary.uploader.upload_large(path, **opts)
        else:
            resp = cloudinary.uploader.upload(path, **opts)
        return resp
    except Exception as e:
        logger.exception("Cloudinary upload failed")
        raise