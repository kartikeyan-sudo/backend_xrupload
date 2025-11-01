import os
import tempfile
import pytest
import cv2
import numpy as np
import cloudinary.uploader

from app.cloudinary_utils import configure_cloudinary, upload_video_to_cloudinary


@pytest.mark.integration
def test_cloudinary_upload_and_cleanup():
    """Integration test: upload a tiny synthetic video to Cloudinary and then delete it.

    This test requires valid Cloudinary credentials available via environment
    variables (or backend/.env). It is marked as an integration test.
    """
    if not configure_cloudinary():
        pytest.skip("Cloudinary credentials not configured")

    # create a tiny synthetic mp4
    h, w, fps = 64, 64, 5
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(tmp_path, fourcc, fps, (w, h))
    for i in range(6):
        frame = (np.ones((h, w, 3), dtype="uint8") * (i * 30)).astype("uint8")
        out.write(frame)
    out.release()

    # upload
    folder = os.getenv("DEFAULT_CLOUD_FOLDER")
    resp = upload_video_to_cloudinary(tmp_path, folder=folder)
    assert isinstance(resp, dict)
    assert ("secure_url" in resp) or ("url" in resp)

    # cleanup remote asset if public_id provided
    public_id = resp.get("public_id")
    if public_id:
        try:
            cloudinary.uploader.destroy(public_id, resource_type="video")
        except Exception:
            # don't fail the test on cleanup errors
            pass

    # local cleanup
    try:
        os.unlink(tmp_path)
    except Exception:
        pass
