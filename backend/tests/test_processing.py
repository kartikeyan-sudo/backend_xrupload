import os
import numpy as np
import tempfile
import cv2
from app.processing import process_video


def create_test_video(path: str, frames: int = 30, fps: int = 10):
    w, h = 320, 240
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(path, fourcc, fps, (w, h))
    for i in range(frames):
        frame = (255 * (i % 2) * np.ones((h, w, 3), dtype="uint8"))
        out.write(frame)
    out.release()


def test_process_video_creates_output(tmp_path):
    import numpy as np

    in_path = os.path.join(tmp_path, "in.mp4")
    out_path = os.path.join(tmp_path, "out.mp4")

    # create a very small synthetic video
    w, h, fps = 160, 120, 5
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(in_path, fourcc, fps, (w, h))
    for i in range(10):
        frame = (np.zeros((h, w, 3), dtype="uint8") + (i * 25)).astype("uint8")
        writer.write(frame)
    writer.release()

    meta = process_video(in_path, out_path)
    assert os.path.exists(out_path)
    assert meta["frames_processed"] > 0
