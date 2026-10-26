"""Unit tests for ActivityClassifier and biomechanical posture classification."""

from datetime import datetime, timezone
import pytest
from src.core.schemas import (
    ActivityCode,
    BoundingBox,
    Point2D,
    TrackLifecycle,
    TrackObservation,
    ZoneType
)
from src.perception.activity import ActivityClassifier, TemporalModalFilter


def create_mock_track(
    track_id: int,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    zone_id: str = "ZONE-DESK-1",
    confidence: float = 0.90,
    velocity: float = 0.0
) -> TrackObservation:
    box = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
    return TrackObservation(
        track_id=track_id,
        ephemeral_hash=f"TRK-{track_id:04d}",
        camera_id="CAM-01",
        box=box,
        footprint=box.footprint,
        detection_confidence=confidence,
        tracking_state=TrackLifecycle.CONFIRMED,
        current_zone_id=zone_id,
        activity_code=ActivityCode.ACT_07,
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc),
        velocity=velocity
    )


class TestActivityClassifier:
    """Verifies that activity classifications are accurate and avoid false positive collaboration."""

    def test_seated_occupants_at_adjacent_desks_are_not_collaborating(self):
        """Regression test for ACT-05 over-reporting:
        Two people seated at adjacent desks (distance 0.12) must be ACT-01 (Seated at Workstation),
        NOT ACT-05 (Active Collaboration).
        """
        clf = ActivityClassifier()

        # Desk 1: Seated human (aspect ratio 1.5, width 0.10, height 0.15)
        track1 = create_mock_track(1, x1=0.20, y1=0.30, x2=0.30, y2=0.45, zone_id="ZONE-DESK-A")
        # Desk 2: Seated human adjacent (distance ~0.12 apart)
        track2 = create_mock_track(2, x1=0.32, y1=0.30, x2=0.42, y2=0.45, zone_id="ZONE-DESK-B")

        act1, conf1 = clf.classify_frame(track1, [track1, track2], ZoneType.WORKSTATION)
        act2, conf2 = clf.classify_frame(track2, [track1, track2], ZoneType.WORKSTATION)

        assert act1 == ActivityCode.ACT_01
        assert act2 == ActivityCode.ACT_01

    def test_standing_occupant_at_workstation(self):
        clf = ActivityClassifier()
        # Standing human at desk: height 0.35, width 0.12 -> aspect ratio ~ 2.9
        track = create_mock_track(1, x1=0.20, y1=0.20, x2=0.32, y2=0.55, zone_id="ZONE-DESK-A")
        act, conf = clf.classify_frame(track, [track], ZoneType.WORKSTATION)
        assert act == ActivityCode.ACT_02

    def test_walking_in_corridor(self):
        clf = ActivityClassifier()
        # Person moving along corridor with velocity 0.05
        track = create_mock_track(1, x1=0.50, y1=0.20, x2=0.60, y2=0.45, zone_id="ZONE-CORRIDOR", velocity=0.05)
        act, conf = clf.classify_frame(track, [track], ZoneType.CORRIDOR)
        assert act == ActivityCode.ACT_03

    def test_collaboration_in_meeting_zone(self):
        clf = ActivityClassifier()
        # Two people in meeting room zone
        track1 = create_mock_track(1, x1=0.60, y1=0.60, x2=0.70, y2=0.80, zone_id="ZONE-MEETING")
        track2 = create_mock_track(2, x1=0.68, y1=0.60, x2=0.78, y2=0.80, zone_id="ZONE-MEETING")
        act1, _ = clf.classify_frame(track1, [track1, track2], ZoneType.MEETING)
        assert act1 == ActivityCode.ACT_05

    def test_low_confidence_detection_defaults_to_unknown(self):
        clf = ActivityClassifier()
        track = create_mock_track(1, x1=0.1, y1=0.1, x2=0.2, y2=0.3, confidence=0.25)
        act, conf = clf.classify_frame(track, [track], ZoneType.WORKSTATION)
        assert act == ActivityCode.ACT_07
