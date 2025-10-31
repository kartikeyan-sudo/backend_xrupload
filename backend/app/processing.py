import cv2
import numpy as np
import os
from datetime import datetime


def process_video(input_path: str, output_path: str, update_progress=None) -> dict:
    """Detect motion and write annotated video.

    update_progress: optional callback(progress_float 0-1, message)
    Returns metadata dict: frames_processed, fps, output_path
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError("Cannot open input video")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    # TODOs:
    # - Extract and return motion metadata (timestamps and bounding boxes) for each frame.
    # - Optionally emit progress via SSE/WebSocket callback rather than polling.
    # - Consider more robust tracking (e.g., centroid/object trackers) for persistent IDs.

    # Try H264 with mp4 container; fall back to mp4v
    fourcc = cv2.VideoWriter_fourcc(*"avc1")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Params for motion detection
    ret, prev = cap.read()
    if not ret:
        out.release()
        cap.release()
        raise RuntimeError("Empty video or cannot read frames")

    prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    frame_idx = 1
    frames_processed = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Frame difference
        diff = cv2.absdiff(prev_gray, gray)
        blur = cv2.GaussianBlur(diff, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 25, 255, cv2.THRESH_BINARY)
        # Morph ops to remove noise
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        for cnt in contours:
            if cv2.contourArea(cnt) < 500:  # skip small areas
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            motion_detected = True

        # Overlay timestamp, frame number, and label
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        label = "MOTION" if motion_detected else "NO MOTION"
        cv2.putText(frame, f"{ts}", (10, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"Frame: {frame_idx}", (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (255, 255, 255), 1)
        # Label box
        color = (0, 0, 255) if motion_detected else (180, 180, 180)
        cv2.rectangle(frame, (width - 140, 10), (width - 10, 40), color, -1)
        cv2.putText(frame, label, (width - 130, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

        out.write(frame)

        prev_gray = gray
        frame_idx += 1
        frames_processed += 1

        if update_progress and total_frames:
            update_progress(frames_processed / total_frames, f"Processing frame {frames_processed}/{total_frames}")

    out.release()
    cap.release()

    return {"frames_processed": frames_processed, "fps": fps, "output_path": output_path}
