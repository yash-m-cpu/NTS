"""Video ingestion, RTSP handling, and mailbox frame buffering.

Remediates BUG-03 (zero seek on live streams), enforces RTSP over TCP,
and implements a single-slot mailbox buffer guaranteeing real-time delivery.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Generator, Optional, Tuple, Union
import cv2
import numpy as np

from src.core.config import settings
from src.core.logging import logger
from src.core.security import sanitize_rtsp_url


class MailboxFrameBuffer:
    """Thread-safe single-slot mailbox buffer guaranteeing sub-second latency."""

    def __init__(self, maxsize: int = 2):
        self._maxsize = maxsize
        self._buffer: Optional[Tuple[np.ndarray, float, int]] = None
        self._lock = threading.Lock()
        self._new_frame_event = threading.Event()
        self._dropped_frames_count = 0
        self._total_frames_received = 0

    def put(self, frame: np.ndarray, timestamp_monotonic: float, frame_idx: int) -> None:
        """Pushes the freshest frame, atomically overwriting older unread frames."""
        with self._lock:
            if self._buffer is not None:
                self._dropped_frames_count += 1
            self._buffer = (frame, timestamp_monotonic, frame_idx)
            self._total_frames_received += 1
            self._new_frame_event.set()

    def get(self, timeout: float = 1.0) -> Tuple[np.ndarray, float, int]:
        """Pops the freshest available frame, blocking up to timeout if empty."""
        if not self._new_frame_event.wait(timeout):
            raise TimeoutError("Frame mailbox starved: no frames received within timeout.")
        with self._lock:
            if self._buffer is None:
                raise TimeoutError("Buffer empty upon wake.")
            frame, ts, idx = self._buffer
            self._buffer = None
            self._new_frame_event.clear()
            return frame, ts, idx

    @property
    def dropped_frames(self) -> int:
        with self._lock:
            return self._dropped_frames_count

    @property
    def total_frames(self) -> int:
        with self._lock:
            return self._total_frames_received


class VideoIngestWorker:
    """Acquires, decodes, and timestamps frames from RTSP streams or video files."""

    def __init__(
        self,
        source: Union[str, int],
        camera_id: str = "CAM-01",
        target_fps: float = settings.TARGET_FPS,
        is_live_stream: Optional[bool] = None
    ):
        self.source = source
        self.camera_id = camera_id
        self.target_fps = target_fps
        self.mailbox = MailboxFrameBuffer(maxsize=settings.MAILBOX_MAXSIZE)

        # Detect source type
        if is_live_stream is not None:
            self.is_live = is_live_stream
        elif isinstance(source, int):
            self.is_live = True
        elif isinstance(source, str) and (source.startswith("rtsp://") or source.startswith("http://")):
            self.is_live = True
        else:
            self.is_live = False

        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_connected = False
        self._reconnect_delay = 1.0
        self._frame_count = 0
        self._start_monotonic = 0.0

    def start(self) -> None:
        """Starts the background ingestion thread."""
        if self._worker_thread and self._worker_thread.is_alive():
            logger.warning(f"Ingest worker for {self.camera_id} is already running.")
            return

        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._ingest_loop,
            name=f"Ingest-{self.camera_id}",
            daemon=True
        )
        self._worker_thread.start()
        logger.info(f"Started video ingest worker for camera {self.camera_id} (Source: {sanitize_rtsp_url(str(self.source))})")

    def stop(self) -> None:
        """Signals the ingestion loop to stop and releases resources."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=3.0)
        self._release_capture()
        logger.info(f"Stopped video ingest worker for camera {self.camera_id}.")

    def _open_capture(self) -> bool:
        """Opens video capture with TCP protocol enforcement for RTSP."""
        self._release_capture()

        # Sanitize for logging
        safe_source = sanitize_rtsp_url(str(self.source))

        if isinstance(self.source, str) and self.source.startswith("rtsp://"):
            # Set RTSP transport to TCP via environment / OpenCV backend
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            self._cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
        else:
            self._cap = cv2.VideoCapture(self.source)

        if not self._cap or not self._cap.isOpened():
            logger.error(f"Failed to open video source: {safe_source}")
            self._is_connected = False
            return False

        self._is_connected = True
        self._reconnect_delay = 1.0
        logger.info(f"Successfully opened video source: {safe_source}")
        return True

    def _release_capture(self) -> None:
        if self._cap:
            try:
                self._cap.release()
            except Exception as e:
                logger.debug(f"Error releasing capture handle: {e}")
            self._cap = None
        self._is_connected = False

    def _ingest_loop(self) -> None:
        """Continuously reads frames and delivers them to the mailbox buffer."""
        self._start_monotonic = time.monotonic()
        frame_delay = 1.0 / self.target_fps if self.target_fps > 0 else 0.033

        while not self._stop_event.is_set():
            if not self._is_connected:
                if not self._open_capture():
                    # Exponential backoff for live streams
                    if self.is_live:
                        time.sleep(self._reconnect_delay)
                        self._reconnect_delay = min(self._reconnect_delay * 2.0, 30.0)
                        continue
                    else:
                        logger.error(f"Recorded video file ended or unreadable: {self.source}")
                        break

            ret, frame = self._cap.read()
            if not ret or frame is None:
                if self.is_live:
                    logger.warning(f"Stream dropped on {self.camera_id}, reconnecting...")
                    self._is_connected = False
                    continue
                else:
                    # Video file reached EOF -> loop seamlessly from beginning
                    logger.info(f"Video file reached EOF; looping: {self.source}")
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self._cap.read()
                    if not ret or frame is None:
                        # Fallback re-open
                        if not self._open_capture():
                            break
                        ret, frame = self._cap.read()
                        if not ret or frame is None:
                            break

            self._frame_count += 1
            now_monotonic = time.monotonic()

            # Push to mailbox
            self.mailbox.put(frame, now_monotonic, self._frame_count)

            # Throttle for recorded video files to match target FPS
            if not self.is_live:
                time.sleep(frame_delay)

        self._release_capture()

    def get_frame(self, timeout: float = 1.0) -> Tuple[np.ndarray, float, int]:
        """Fetches the latest frame from the mailbox buffer."""
        return self.mailbox.get(timeout=timeout)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def frames_processed(self) -> int:
        return self._frame_count
