"""Perception pipeline coordinator and streaming service.

Coordinates video ingestion, detection, tracking, spatial mapping,
activity debouncing, and overlay generation in a background execution loop.
"""

import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union
import cv2
import numpy as np

from src.core.config import settings
from src.core.logging import logger
from src.core.schemas import (
    ActivityCode,
    LiveTelemetryMessage,
    OccupancyState,
    TrackObservation,
    TrackTelemetry,
    ZoneRead,
    ZoneType
)
from src.export.overlay import OverlayRenderer
from src.perception.activity import ActivityClassifier, TemporalModalFilter
from src.perception.detector import YOLOPersonDetector
from src.perception.ingest import VideoIngestWorker
from src.perception.spatial import WorkstationState, ZoneManager
from src.perception.tracker import MultiPersonTracker
from src.storage.database import SessionLocal
from src.storage.repository import TelemetryRepository


class PerceptionPipeline:
    """Manages real-time computer vision perception for a specific camera feed."""

    def __init__(
        self,
        camera_id: str = "CAM-01",
        source: Optional[Union[str, int]] = None
    ):
        self.camera_id = camera_id
        self.source = source or settings.SAMPLE_VIDEO_PATH or 0

        # Core perception modules
        self.ingest_worker = VideoIngestWorker(source=self.source, camera_id=camera_id)
        self.detector = YOLOPersonDetector()
        self.tracker = MultiPersonTracker(camera_id=camera_id)
        self.zone_mgr = ZoneManager()
        self.activity_clf = ActivityClassifier()
        self.modal_filter = TemporalModalFilter()
        self.renderer = OverlayRenderer()

        # Zone state machines
        self.workstation_states: Dict[str, WorkstationState] = {}
        for z in self.zone_mgr.list_zones(self.camera_id):
            self.workstation_states[z.zone_id] = WorkstationState(z.zone_id)

        # Thread synchronization & state
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Latest frame & telemetry cache
        self.latest_raw_frame: Optional[np.ndarray] = None
        self.latest_annotated_frame: Optional[np.ndarray] = None
        self.latest_tracks: List[TrackObservation] = []
        self.latest_fps: float = 0.0

        # Rolling statistics (5-minute rolling window)
        self.rolling_activity_counts: Dict[str, int] = defaultdict(int)
        self.rolling_desk_occupied_seconds: float = 0.0
        self.rolling_monitored_seconds: float = 0.0

    def start(self) -> None:
        """Starts ingestion and processing threads."""
        if self._thread and self._thread.is_alive():
            logger.warning(f"Pipeline for {self.camera_id} is already running.")
            return

        self._stop_event.clear()
        self.ingest_worker.start()

        self._thread = threading.Thread(
            target=self._process_loop,
            name=f"Perception-{self.camera_id}",
            daemon=True
        )
        self._thread.start()
        logger.info(f"Perception pipeline started for {self.camera_id}.")

    def stop(self) -> None:
        """Stops the perception pipeline."""
        self._stop_event.set()
        self.ingest_worker.stop()
        if self._thread:
            self._thread.join(timeout=3.0)
        logger.info(f"Perception pipeline stopped for {self.camera_id}.")

    def set_source(self, new_source: Union[str, int, Path], restart: bool = True) -> None:
        """Dynamically switches the video source (e.g. newly uploaded video) and reinitializes pipeline."""
        was_running = self._thread is not None and self._thread.is_alive()
        if was_running:
            self.stop()

        self.source = str(new_source) if isinstance(new_source, Path) else new_source
        self.ingest_worker = VideoIngestWorker(source=self.source, camera_id=self.camera_id)

        with self._lock:
            self.latest_raw_frame = None
            self.latest_annotated_frame = None
            self.latest_tracks = []
            self.latest_fps = 0.0
            self.rolling_activity_counts.clear()
            self.rolling_desk_occupied_seconds = 0.0
            self.rolling_monitored_seconds = 0.0

        if was_running or restart:
            self.start()
        logger.info(f"Perception pipeline for {self.camera_id} switched to source: {self.source}")


    def _process_loop(self) -> None:
        """Main frame processing loop."""
        prev_time = time.monotonic()

        while not self._stop_event.is_set():
            try:
                frame, timestamp_monotonic, frame_idx = self.ingest_worker.get_frame(timeout=0.5)
            except TimeoutError:
                continue

            now = time.monotonic()
            dt = max(0.001, now - prev_time)
            prev_time = now
            self.latest_fps = 0.9 * self.latest_fps + 0.1 * (1.0 / dt)

            # 1. Person Detection
            detections = self.detector.detect(frame)

            # 2. Multi-Object Tracking
            tracks = self.tracker.update(detections)

            # 3. Zone Matching & Activity Classification
            zones = self.zone_mgr.list_zones(self.camera_id)
            zone_occupants: Dict[str, List[TrackObservation]] = defaultdict(list)

            for trk in tracks:
                matched_zone_id = self.zone_mgr.match_zone(trk.footprint, self.camera_id)
                trk.current_zone_id = matched_zone_id
                if matched_zone_id:
                    zone_occupants[matched_zone_id].append(trk)

                z = self.zone_mgr.get_zone(matched_zone_id) if matched_zone_id else None
                z_type = z.zone_type if z else None

                raw_act, conf = self.activity_clf.classify_frame(trk, tracks, z_type)
                smoothed_act = self.modal_filter.update(trk.track_id, raw_act)
                trk.activity_code = smoothed_act

                # Update single track telemetry state
                single_track = self.tracker.tracks.get(trk.track_id)
                if single_track:
                    if single_track.last_zone_id is not None and matched_zone_id != single_track.last_zone_id:
                        single_track.transitions_count += 1
                        single_track.dwell_seconds = 0.0
                    single_track.last_zone_id = matched_zone_id
                    single_track.current_zone_id = matched_zone_id
                    single_track.current_activity_code = smoothed_act.value
                    single_track.activity_counts[smoothed_act.value] = single_track.activity_counts.get(smoothed_act.value, 0) + 1
                    single_track.dwell_seconds += dt

                    # Waiting accumulation in corridors or shared resources
                    if z_type in (ZoneType.SHARED_RESOURCE, ZoneType.CORRIDOR) and single_track.velocity < 0.025:
                        single_track.waiting_seconds += dt

                    # Interruption detection: peer approach while seated at workstation
                    if smoothed_act == ActivityCode.ACT_01 and len(tracks) > 1:
                        for other in tracks:
                            if other.track_id != trk.track_id:
                                dx = trk.footprint.x - other.footprint.x
                                dy = trk.footprint.y - other.footprint.y
                                dist = (dx * dx + dy * dy) ** 0.5
                                if dist < 0.08 and (now - single_track.last_interruption_time) > 15.0:
                                    other_st = self.tracker.tracks.get(other.track_id)
                                    if other_st and (other_st.velocity > 0.02 or other.activity_code in (ActivityCode.ACT_02, ActivityCode.ACT_03, ActivityCode.ACT_05)):
                                        single_track.interruption_events += 1
                                        single_track.last_interruption_time = now

                    # Sync accumulated metrics back to trk observation
                    trk.dwell_duration_seconds = round(single_track.dwell_seconds, 1)
                    trk.transitions_count = single_track.transitions_count
                    trk.interruption_events = single_track.interruption_events
                    trk.waiting_seconds = round(single_track.waiting_seconds, 1)
                    total_act = sum(single_track.activity_counts.values())
                    if total_act > 0:
                        trk.activity_breakdown = {
                            k.split(":")[0].strip(): round(v / total_act * 100.0, 1)
                            for k, v in single_track.activity_counts.items()
                        }
                    else:
                        short_k = smoothed_act.value.split(":")[0].strip()
                        trk.activity_breakdown = {short_k: 100.0}

                # Track rolling activity distribution
                self.rolling_activity_counts[smoothed_act.value] += 1

            # 4. Update Workstation Occupancy State Machines
            for zid, ws in self.workstation_states.items():
                present_in_zone = zone_occupants.get(zid, [])
                ws.update(present_in_zone, dt)

            # 5. Render Visual Overlays
            rolling_wor = self.get_rolling_wor()
            annotated = self.renderer.render(
                frame=frame,
                tracks=tracks,
                zones=zones,
                camera_id=self.camera_id,
                fps=self.latest_fps,
                rolling_wor_pct=rolling_wor
            )

            # 6. Update Thread-Safe Cache
            with self._lock:
                self.latest_raw_frame = frame
                self.latest_annotated_frame = annotated
                self.latest_tracks = tracks

            # 7. Periodic Asynchronous Database Persistence (every 15 frames ~ 1s)
            if frame_idx % 15 == 0:
                self._persist_telemetry_batch(tracks, zone_occupants)

    def _persist_telemetry_batch(
        self,
        tracks: List[TrackObservation],
        zone_occupants: Dict[str, List[TrackObservation]]
    ) -> None:
        """Appends lightweight events to SQLite database."""
        try:
            with SessionLocal() as db:
                for zid, occupants in zone_occupants.items():
                    if occupants:
                        TelemetryRepository.record_occupancy_event(
                            db=db,
                            zone_id=zid,
                            track_hash=occupants[0].ephemeral_hash,
                            state="OCCUPIED",
                            duration_seconds=1.0
                        )
                for trk in tracks:
                    TelemetryRepository.record_activity_event(
                        db=db,
                        track_hash=trk.ephemeral_hash,
                        zone_id=trk.current_zone_id,
                        activity_code=trk.activity_code.value,
                        confidence=trk.detection_confidence,
                        duration_seconds=1.0
                    )
        except Exception as e:
            logger.debug(f"Telemetry persistence warning: {e}")

    def get_annotated_jpeg(self) -> Optional[bytes]:
        """Encodes the latest annotated frame into JPEG format."""
        with self._lock:
            if self.latest_annotated_frame is None:
                return None
            ret, jpeg = cv2.imencode(".jpg", self.latest_annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return jpeg.tobytes() if ret else None

    def get_live_telemetry_snapshot(self) -> LiveTelemetryMessage:
        """Returns the current state formatted as a LiveTelemetryMessage schema."""
        with self._lock:
            track_items: List[TrackTelemetry] = []
            h = 720
            w = 1280
            if self.latest_annotated_frame is not None:
                h, w = self.latest_annotated_frame.shape[:2]

            for trk in self.latest_tracks:
                b = trk.box
                box_px = [int(b.x1 * w), int(b.y1 * h), int(b.x2 * w), int(b.y2 * h)]
                foot_px = [int(trk.footprint.x * w), int(trk.footprint.y * h)]

                track_items.append(
                    TrackTelemetry(
                        track_id=trk.ephemeral_hash,
                        box=box_px,
                        footprint=foot_px,
                        zone_id=trk.current_zone_id,
                        activity=trk.activity_code.value,
                        confidence=round(trk.detection_confidence, 2),
                        rolling_wor_pct=self.get_rolling_wor(),
                        velocity=getattr(trk, "velocity", 0.0),
                        dwell_duration_seconds=getattr(trk, "dwell_duration_seconds", 0.0),
                        transitions_count=getattr(trk, "transitions_count", 0),
                        interruption_events=getattr(trk, "interruption_events", 0),
                        waiting_seconds=getattr(trk, "waiting_seconds", 0.0),
                        activity_breakdown=getattr(trk, "activity_breakdown", {})
                    )
                )

            zones_dict = {
                zid: ws.state.value
                for zid, ws in self.workstation_states.items()
            }

            return LiveTelemetryMessage(
                timestamp=datetime.now(timezone.utc).isoformat(),
                camera_id=self.camera_id,
                fps=round(self.latest_fps, 1),
                active_tracks=track_items,
                zones_occupancy=zones_dict,
                observation_coverage_pct=100.0 if self.ingest_worker.is_connected else 0.0
            )

    def get_rolling_wor(self) -> float:
        """Computes rolling Workstation Occupancy Rate across all monitored desks."""
        total_time = sum(ws.total_occupied_seconds for ws in self.workstation_states.values())
        desk_count = len([z for z in self.zone_mgr.list_zones(self.camera_id) if z.zone_type.value == "WORKSTATION"]) or 1
        return round(min(100.0, (total_time / max(1.0, desk_count * 60.0)) * 100.0), 1)

    def get_activity_distribution(self) -> Dict[str, float]:
        """Returns rolling percentage share across all 7 activity classes."""
        total = sum(self.rolling_activity_counts.values())
        if total <= 0:
            return {f"ACT-0{i}": 0.0 for i in range(1, 8)}
        return {
            k.split(":")[0]: round(100.0 * (v / total), 1)
            for k, v in self.rolling_activity_counts.items()
        }


# Singleton pipeline registry for multiple cameras
_pipelines: Dict[str, PerceptionPipeline] = {}


def get_pipeline(camera_id: str = "CAM-01") -> PerceptionPipeline:
    """Returns or creates the perception pipeline singleton for a camera."""
    if camera_id not in _pipelines:
        _pipelines[camera_id] = PerceptionPipeline(camera_id=camera_id)
        _pipelines[camera_id].start()
    return _pipelines[camera_id]
