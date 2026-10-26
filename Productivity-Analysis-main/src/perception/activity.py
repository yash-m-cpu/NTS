"""Physical activity classification and temporal modal filtering.

Classifies human bodies into 7 mutually exclusive physical states (ACT-01 to ACT-07)
without psychological or affective inference, applying a rolling modal filter.
"""

from collections import Counter, deque
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.core.config import settings
from src.core.schemas import (
    ActivityCode,
    Point2D,
    TrackObservation,
    ZoneType
)


class ActivityClassifier:
    """Classifies physical posture and motion states from spatial track features."""

    def __init__(
        self,
        walking_speed_threshold: float = 0.035,  # Normalized velocity units / s
        collaboration_distance: float = 0.075    # Normalized distance threshold (~70-90px on 1080p)
    ):
        self.walking_speed_threshold = walking_speed_threshold
        self.collaboration_distance = collaboration_distance

    def classify_frame(
        self,
        track: TrackObservation,
        all_tracks: List[TrackObservation],
        zone_type: Optional[ZoneType] = None
    ) -> Tuple[ActivityCode, float]:
        """Evaluates instantaneous raw posture for a track in a single frame.

        Returns:
            Tuple of (ActivityCode, confidence_score)
        """
        # Low confidence or missing detection defaults to Unknown
        if track.detection_confidence < 0.35:
            return ActivityCode.ACT_07, 0.40

        box = track.box
        aspect_ratio = box.height / (box.width + 1e-6)
        velocity = getattr(track, "velocity", 0.0)

        # Distorted or occluded aspect ratios default to Unknown
        if aspect_ratio < 0.45 or aspect_ratio > 3.6:
            return ActivityCode.ACT_07, 0.45

        # 1. High-speed Locomotion Check (moving across space)
        if velocity >= max(self.walking_speed_threshold * 1.5, 0.055) and (
            zone_type != ZoneType.WORKSTATION or velocity > 0.08
        ):
            return ActivityCode.ACT_03, 0.88

        # 2. Workstation Zone Analysis
        if zone_type == ZoneType.WORKSTATION:
            # Check for close peer visit in the SAME workstation zone or standing over desk
            if len(all_tracks) > 1:
                for other in all_tracks:
                    if other.track_id != track.track_id:
                        # Case A: Another person has entered this exact same workstation zone
                        if other.current_zone_id == track.current_zone_id:
                            return ActivityCode.ACT_05, 0.88

                        # Case B: Another person is standing immediately adjacent (< 0.075) consulting
                        dx = track.footprint.x - other.footprint.x
                        dy = track.footprint.y - other.footprint.y
                        dist = np.sqrt(dx * dx + dy * dy)
                        other_ar = other.box.height / (other.box.width + 1e-6)
                        if dist <= self.collaboration_distance:
                            # Only collaboration if one is standing and other is seated/visiting
                            if (aspect_ratio >= 1.90 and other_ar < 1.90) or (aspect_ratio < 1.90 and other_ar >= 1.90):
                                return ActivityCode.ACT_05, 0.86

            # Biomechanical aspect ratio: seated humans have lower height-to-width ratio (< 1.90)
            if aspect_ratio < 1.90:
                # Active reaching / mouse & keyboard motion or steady focus
                if 0.012 <= velocity < 0.045:
                    return ActivityCode.ACT_04, 0.84  # Workstation interaction
                return ActivityCode.ACT_01, 0.92      # Seated at workstation
            else:
                return ActivityCode.ACT_02, 0.88      # Standing at workstation

        # 3. Collaboration & Meeting Zones
        if zone_type in (ZoneType.COLLABORATION, ZoneType.MEETING):
            if len(all_tracks) > 1:
                for other in all_tracks:
                    if other.track_id != track.track_id:
                        if other.current_zone_id == track.current_zone_id:
                            return ActivityCode.ACT_05, 0.90
                        dx = track.footprint.x - other.footprint.x
                        dy = track.footprint.y - other.footprint.y
                        if np.sqrt(dx * dx + dy * dy) <= 0.12:
                            return ActivityCode.ACT_05, 0.88

            # Solo presence in meeting/collab area
            if aspect_ratio < 1.90:
                return ActivityCode.ACT_01, 0.80
            return ActivityCode.ACT_02, 0.80

        # 4. Corridor / Circulation Zones
        if zone_type == ZoneType.CORRIDOR:
            if velocity >= self.walking_speed_threshold or aspect_ratio >= 1.70:
                return ActivityCode.ACT_03, 0.88  # Walking in corridor
            return ActivityCode.ACT_06, 0.80      # Stationary in transit zone

        # 5. Shared Resource Zone (printer, coffee machine, kiosk)
        if zone_type == ZoneType.SHARED_RESOURCE:
            if velocity < self.walking_speed_threshold:
                return ActivityCode.ACT_04, 0.82  # Interacting with shared resource
            return ActivityCode.ACT_03, 0.80

        # 6. Unassigned Space / Common Area
        if len(all_tracks) > 1:
            for other in all_tracks:
                if other.track_id != track.track_id:
                    dx = track.footprint.x - other.footprint.x
                    dy = track.footprint.y - other.footprint.y
                    if np.sqrt(dx * dx + dy * dy) <= 0.065 and velocity < self.walking_speed_threshold:
                        return ActivityCode.ACT_05, 0.85  # Standing huddle / impromptu conversation

        if velocity >= self.walking_speed_threshold:
            return ActivityCode.ACT_03, 0.82

        # Biomechanical posture: Seated human (< 1.85 aspect ratio) and stationary
        if aspect_ratio < 1.85:
            if 0.012 <= velocity < 0.045:
                return ActivityCode.ACT_04, 0.82
            return ActivityCode.ACT_01, 0.88

        # Standing human (aspect ratio >= 1.85)
        if aspect_ratio >= 1.85 and velocity < self.walking_speed_threshold:
            return ActivityCode.ACT_02, 0.82

        if track.current_zone_id is None:
            return ActivityCode.ACT_06, 0.80      # Away from monitored desk

        # Default fallback
        return ActivityCode.ACT_07, 0.50


class TemporalModalFilter:
    """Rolling circular ring buffer debouncing predictions via majority voting."""

    def __init__(self, window_size: int = settings.MODAL_FILTER_WINDOW_FRAMES):
        self.window_size = window_size
        self._buffers: Dict[int, deque] = {}

    def update(self, track_id: int, raw_activity: ActivityCode) -> ActivityCode:
        """Appends raw activity and returns the temporal mode of the window."""
        if track_id not in self._buffers:
            self._buffers[track_id] = deque(maxlen=self.window_size)

        buf = self._buffers[track_id]
        buf.append(raw_activity)

        if not buf:
            return ActivityCode.ACT_07

        # Calculate majority vote
        counts = Counter(buf)
        most_common_class, most_common_count = counts.most_common(1)[0]

        # If majority agreement is < 50%, return Unknown until stabilized
        agreement_ratio = most_common_count / len(buf)
        if len(buf) >= 15 and agreement_ratio < 0.50:
            return ActivityCode.ACT_07

        return most_common_class

    def cleanup(self, active_track_ids: List[int]) -> None:
        """Purges history for expired tracks."""
        active_set = set(active_track_ids)
        to_delete = [tid for tid in self._buffers if tid not in active_set]
        for tid in to_delete:
            del self._buffers[tid]
