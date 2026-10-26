"""Multi-person tracking engine implementing ByteTrack-style association.

Maintains track identities across occlusions, computes ground-plane footprints,
calculates velocity vectors, and assigns ephemeral salted session hashes.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.core.schemas import (
    BoundingBox,
    Detection,
    Point2D,
    TrackLifecycle,
    TrackObservation
)
from src.core.security import generate_ephemeral_track_hash


def compute_iou(boxA: BoundingBox, boxB: BoundingBox) -> float:
    """Computes Intersection over Union (IoU) between two normalized boxes."""
    xA = max(boxA.x1, boxB.x1)
    yA = max(boxA.y1, boxB.y1)
    xB = min(boxA.x2, boxB.x2)
    yB = min(boxA.y2, boxB.y2)

    inter_width = max(0.0, xB - xA)
    inter_height = max(0.0, yB - yA)
    inter_area = inter_width * inter_height

    areaA = boxA.width * boxA.height
    areaB = boxB.width * boxB.height
    union_area = areaA + areaB - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


class SingleTrack:
    """Maintains state for a single tracked human body."""

    def __init__(self, track_id: int, initial_detection: Detection, camera_id: str):
        self.track_id = track_id
        self.camera_id = camera_id
        self.ephemeral_hash = generate_ephemeral_track_hash(track_id, camera_id)

        self.box = initial_detection.box
        self.confidence = initial_detection.confidence
        self.state = TrackLifecycle.TENTATIVE

        now = datetime.now(timezone.utc)
        self.first_seen = now
        self.last_seen = now

        self.hits = 1
        self.total_frames = 1
        self.consecutive_misses = 0

        # Velocity tracking (dx/dt, dy/dt in normalized coordinates per second)
        self.prev_footprint = self.box.footprint
        self.prev_timestamp = now
        self.velocity = 0.0

        # Spatial zone & activity handles
        self.current_zone_id: Optional[str] = None
        self.last_zone_id: Optional[str] = None
        self.current_activity_code: Optional[str] = None

        # Cumulative telemetry metrics
        self.transitions_count: int = 0
        self.interruption_events: int = 0
        self.waiting_seconds: float = 0.0
        self.dwell_seconds: float = 0.0
        self.activity_counts: Dict[str, int] = {}
        self.last_interruption_time: float = 0.0

    def update(self, detection: Detection) -> None:
        """Updates track with a new matched detection."""
        now = datetime.now(timezone.utc)
        dt = (now - self.prev_timestamp).total_seconds()

        curr_footprint = detection.box.footprint
        if dt > 0.001:
            dx = curr_footprint.x - self.prev_footprint.x
            dy = curr_footprint.y - self.prev_footprint.y
            dist = np.sqrt(dx * dx + dy * dy)
            self.velocity = dist / dt

        self.prev_footprint = curr_footprint
        self.prev_timestamp = now

        # Smooth bounding box with simple alpha filter (70% new, 30% old)
        alpha = 0.70
        self.box = BoundingBox(
            x1=alpha * detection.box.x1 + (1 - alpha) * self.box.x1,
            y1=alpha * detection.box.y1 + (1 - alpha) * self.box.y1,
            x2=alpha * detection.box.x2 + (1 - alpha) * self.box.x2,
            y2=alpha * detection.box.y2 + (1 - alpha) * self.box.y2
        )

        self.confidence = detection.confidence
        self.last_seen = now
        self.hits += 1
        self.total_frames += 1
        self.consecutive_misses = 0

        # Promote to confirmed after 3 consecutive hits
        if self.state == TrackLifecycle.TENTATIVE and self.hits >= 3:
            self.state = TrackLifecycle.CONFIRMED

    def mark_missed(self) -> None:
        """Marks track as missed for the current frame."""
        self.consecutive_misses += 1
        self.total_frames += 1
        if self.consecutive_misses > 2:
            self.state = TrackLifecycle.LOST

    def to_observation(self) -> TrackObservation:
        """Serializes track state into a TrackObservation schema."""
        from src.core.schemas import ActivityCode
        act = ActivityCode.ACT_07
        if self.current_activity_code:
            try:
                act = ActivityCode(self.current_activity_code)
            except ValueError:
                act = ActivityCode.ACT_07

        total_act = sum(self.activity_counts.values())
        if total_act > 0:
            breakdown = {
                k.split(":")[0].strip(): round((v / total_act) * 100.0, 1)
                for k, v in self.activity_counts.items()
            }
        else:
            short_k = act.value.split(":")[0].strip()
            breakdown = {short_k: 100.0}

        return TrackObservation(
            track_id=self.track_id,
            ephemeral_hash=self.ephemeral_hash,
            camera_id=self.camera_id,
            box=self.box,
            footprint=self.box.footprint,
            detection_confidence=self.confidence,
            tracking_state=self.state,
            current_zone_id=self.current_zone_id,
            activity_code=act,
            first_seen=self.first_seen,
            last_seen=self.last_seen,
            total_frames=self.total_frames,
            consecutive_invisible_frames=self.consecutive_misses,
            velocity=round(float(self.velocity), 4),
            dwell_duration_seconds=round(float(self.dwell_seconds), 1),
            transitions_count=self.transitions_count,
            interruption_events=self.interruption_events,
            waiting_seconds=round(float(self.waiting_seconds), 1),
            activity_breakdown=breakdown
        )


class MultiPersonTracker:
    """Associates frame detections to tracks using bipartite IoU matching."""

    def __init__(
        self,
        camera_id: str = "CAM-01",
        iou_threshold: float = 0.30,
        max_lost_frames: int = 45  # 3.0 seconds at 15 FPS
    ):
        self.camera_id = camera_id
        self.iou_threshold = iou_threshold
        self.max_lost_frames = max_lost_frames
        self.tracks: Dict[int, SingleTrack] = {}
        self._next_track_id = 1

    def update(self, detections: List[Detection]) -> List[TrackObservation]:
        """Processes detections for the current frame and returns all active tracks."""
        active_track_ids = list(self.tracks.keys())
        num_dets = len(detections)
        num_tracks = len(active_track_ids)

        matched_tracks = set()
        matched_dets = set()

        if num_dets > 0 and num_tracks > 0:
            # Build IoU cost matrix
            iou_matrix = np.zeros((num_tracks, num_dets), dtype=np.float32)
            for i, tid in enumerate(active_track_ids):
                track = self.tracks[tid]
                for j, det in enumerate(detections):
                    iou_matrix[i, j] = compute_iou(track.box, det.box)

            # Greedy bipartite matching (Hungarian approximation)
            matched_pairs = []
            while True:
                max_iou = np.max(iou_matrix)
                if max_iou < self.iou_threshold:
                    break
                i, j = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                matched_pairs.append((active_track_ids[i], j))
                iou_matrix[i, :] = -1.0
                iou_matrix[:, j] = -1.0

            for tid, det_idx in matched_pairs:
                self.tracks[tid].update(detections[det_idx])
                matched_tracks.add(tid)
                matched_dets.add(det_idx)

        # Handle unmatched active tracks (misses)
        for tid in active_track_ids:
            if tid not in matched_tracks:
                self.tracks[tid].mark_missed()

        # Handle unmatched detections (new tracks)
        for j, det in enumerate(detections):
            if j not in matched_dets:
                new_track = SingleTrack(self._next_track_id, det, self.camera_id)
                self.tracks[self._next_track_id] = new_track
                self._next_track_id += 1

        # Purge expired tracks
        expired_ids = [
            tid for tid, track in self.tracks.items()
            if track.consecutive_misses > self.max_lost_frames
        ]
        for tid in expired_ids:
            del self.tracks[tid]

        # Return confirmed or non-expired tracks
        return [
            track.to_observation()
            for track in self.tracks.values()
            if track.consecutive_misses <= self.max_lost_frames
        ]
