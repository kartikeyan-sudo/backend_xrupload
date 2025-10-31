import cv2
import os
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional
from collections import deque
from .cloud import upload_video

logger = logging.getLogger(__name__)

JOBS: Dict[str, Dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)

class SimpleTracker:
    def __init__(self, max_history=5):
        self.history = {}
        self.next_id = 1

    def update(self, centroids):
        assigned = {}
        new_hist = {}
        for c in centroids:
            best_id = None
            best_dist = 1e9
            for id_, dq in self.history.items():
                last = dq[-1]
                d = (last[0] - c[0]) ** 2 + (last[1] - c[1]) ** 2
                if d < best_dist:
                    best_dist = d
                    best_id = id_
            if best_id is None or best_dist > 4000:
                best_id = f"obj{self.next_id}"
                self.next_id += 1
            dq = self.history.get(best_id, deque(maxlen=5))
            dq.append(c)
            new_hist[best_id] = dq
        self.history = new_hist
        smoothed = []
        for id_, dq in self.history.items():
            x = int(sum(p[0] for p in dq) / len(dq))
            y = int(sum(p[1] for p in dq) / len(dq))
            smoothed.append(((x, y), id_))
        return smoothed

def start_job(job_id: str, input_path: str, output_path: str, cloud_folder: Optional[str], max_seconds=600):
    JOBS[job_id] = {"status": "processing", "progress": 0, "message": "started"}

    def _process():
        start_ts = time.time()
        try:
            cap = cv2.VideoCapture(input_path)
            if not cap.isOpened():
                raise RuntimeError("Cannot open video file")
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

            backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=True)
            tracker = SimpleTracker()

            frame_no = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_no += 1
                elapsed = time.time() - start_ts
                if elapsed > max_seconds:
                    raise TimeoutError("Processing time exceeded")

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5, 5), 0)
                fgmask = backSub.apply(blur)

                _, th = cv2.threshold(fgmask, 244, 255, cv2.THRESH_BINARY)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                opening = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)
                closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel, iterations=2)

                contours, _ = cv2.findContours(closing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                centroids = []
                boxes = []
                for c in contours:
                    area = cv2.contourArea(c)
                    if area < 400:
                        continue
                    x, y, bw, bh = cv2.boundingRect(c)
                    boxes.append((x, y, bw, bh))
                    centroids.append((x + bw // 2, y + bh // 2))

                smoothed = tracker.update(centroids)
                for (x, y, bw, bh) in boxes:
                    cv2.rectangle(frame, (x, y), (x + bw, y + bh), (255, 255, 255), 2)
                for (cpos, cid) in smoothed:
                    cv2.putText(frame, cid, (cpos[0] - 10, cpos[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230,230,230), 1)

                cv2.putText(frame, f"Frame: {frame_no}/{total_frames}", (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230,230,230), 1)
                cv2.putText(frame, f"Status: processing", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (230,230,230), 1)

                writer.write(frame)
                if total_frames > 0:
                    JOBS[job_id]["progress"] = int(frame_no / total_frames * 80)
                else:
                    JOBS[job_id]["progress"] = min(80, JOBS[job_id].get("progress", 0) + 1)

            cap.release()
            writer.release()

            JOBS[job_id]["progress"] = 85
            JOBS[job_id]["message"] = "uploading to cloud"
            JOBS[job_id]["status"] = "uploading"

            cloud_folder = cloud_folder or "xrcc"
            public_id = f"job_{job_id}"
            resp = upload_video(output_path, folder=cloud_folder, public_id=public_id)
            JOBS[job_id]["progress"] = 100
            JOBS[job_id]["status"] = "done"
            JOBS[job_id]["message"] = "completed"
            JOBS[job_id]["result_url"] = resp.get("secure_url") or resp.get("url")

            try:
                os.remove(input_path)
            except Exception:
                pass
            try:
                os.remove(output_path)
            except Exception:
                pass

        except Exception as e:
            logger.exception("Job %s failed", job_id)
            JOBS[job_id]["status"] = "error"
            JOBS[job_id]["error"] = str(e)
            JOBS[job_id]["message"] = "failed"

    _executor.submit(_process)