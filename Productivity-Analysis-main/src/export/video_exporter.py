"""On-demand MP4 video export engine with burned-in telemetry.

Executes detection, tracking, zone mapping, and overlay rendering
over a specified video clip or time range, producing an MP4 file with zero audio.
"""

import os
import threading
import time
from pathlib import Path
from typing import Callable, Optional
import cv2

from src.core.config import settings
from src.core.logging import logger
from src.export.overlay import OverlayRenderer
from src.perception.activity import ActivityClassifier, TemporalModalFilter
from src.perception.detector import YOLOPersonDetector
from src.perception.spatial import ZoneManager
from src.perception.tracker import MultiPersonTracker


class VideoExportJob:
    """Manages execution and status for an individual MP4 video export job."""

    def __init__(
        self,
        job_id: str,
        source_path: Path,
        output_path: Path,
        camera_id: str = "CAM-01",
        max_frames: Optional[int] = None
    ):
        self.job_id = job_id
        self.source_path = Path(source_path)
        self.output_path = Path(output_path)
        self.camera_id = camera_id
        self.max_frames = max_frames

        self.status = "QUEUED"  # QUEUED, RENDERING, READY, ERROR
        self.progress_pct: float = 0.0
        self.frames_rendered: int = 0
        self.total_frames: int = 0
        self.error_message: Optional[str] = None

        self._thread: Optional[threading.Thread] = None

    def start_async(self) -> None:
        """Starts the export rendering thread in the background."""
        self._thread = threading.Thread(target=self._run_export, daemon=True)
        self._thread.start()

    def _run_export(self) -> None:
        """Executes full frame-by-frame perception and overlay rendering."""
        self.status = "RENDERING"
        logger.info(f"Starting export job {self.job_id} from {self.source_path} to {self.output_path}")

        if not self.source_path.exists():
            self.status = "ERROR"
            self.error_message = f"Source video not found: {self.source_path}"
            logger.error(self.error_message)
            return

        cap = cv2.VideoCapture(str(self.source_path))
        if not cap.isOpened():
            self.status = "ERROR"
            self.error_message = f"Failed to open video file: {self.source_path}"
            logger.error(self.error_message)
            return

        total_cap_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or settings.TARGET_FPS
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720

        self.total_frames = min(total_cap_frames, self.max_frames) if self.max_frames else total_cap_frames
        if self.total_frames <= 0:
            self.total_frames = 100

        # Initialize export destination
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(self.output_path), fourcc, fps, (w, h))

        if not writer.isOpened():
            self.status = "ERROR"
            self.error_message = f"Failed to initialize VideoWriter for {self.output_path}"
            logger.error(self.error_message)
            cap.release()
            return

        # Initialize perception modules
        detector = YOLOPersonDetector()
        tracker = MultiPersonTracker(camera_id=self.camera_id)
        zone_mgr = ZoneManager()
        classifier = ActivityClassifier()
        modal_filter = TemporalModalFilter()
        renderer = OverlayRenderer()

        zones = zone_mgr.list_zones(self.camera_id)

        try:
            while cap.isOpened():
                if self.max_frames and self.frames_rendered >= self.max_frames:
                    break

                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                # 1. Detect humans
                detections = detector.detect(frame)

                # 2. Track identities
                tracks = tracker.update(detections)

                # 3. Spatial zone assignment & activity classification
                for trk in tracks:
                    matched_zone_id = zone_mgr.match_zone(trk.footprint, self.camera_id)
                    trk.current_zone_id = matched_zone_id

                    z = zone_mgr.get_zone(matched_zone_id) if matched_zone_id else None
                    z_type = z.zone_type if z else None

                    raw_act, conf = classifier.classify_frame(trk, tracks, z_type)
                    smoothed_act = modal_filter.update(trk.track_id, raw_act)
                    trk.activity_code = smoothed_act

                # 4. Render overlays
                annotated_frame = renderer.render(
                    frame=frame,
                    tracks=tracks,
                    zones=zones,
                    camera_id=self.camera_id,
                    fps=fps,
                    rolling_wor_pct=75.0 if any(t.current_zone_id for t in tracks) else 0.0
                )

                # 5. Write to output MP4
                writer.write(annotated_frame)
                self.frames_rendered += 1
                self.progress_pct = round(100.0 * (self.frames_rendered / max(1, self.total_frames)), 1)

            self.status = "READY"
            logger.info(f"Export job {self.job_id} completed successfully. Rendered {self.frames_rendered} frames.")
        except Exception as e:
            self.status = "ERROR"
            self.error_message = str(e)
            logger.error(f"Error during video export job {self.job_id}: {e}")
        finally:
            cap.release()
            writer.release()
