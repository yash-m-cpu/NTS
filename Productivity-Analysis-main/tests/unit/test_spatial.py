"""Unit tests for spatial geometry, point-in-polygon ray casting, and zone state machine."""

import time
import pytest
from src.core.schemas import ZoneCreate
from src.perception.spatial import (
    WorkstationState,
    ZoneManager,
    point_in_polygon
)


class TestPointInPolygon:
    """Tests ray-casting point-in-polygon algorithm."""

    def test_convex_polygon(self):
        # Unit square [0.2, 0.2] to [0.8, 0.8]
        poly = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]

        assert point_in_polygon((0.5, 0.5), poly) is True
        assert point_in_polygon((0.1, 0.5), poly) is False
        assert point_in_polygon((0.5, 0.9), poly) is False
        assert point_in_polygon((0.9, 0.9), poly) is False

    def test_concave_l_shaped_polygon(self):
        # L-shaped polygon
        poly = [
            [0.0, 0.0],
            [0.4, 0.0],
            [0.4, 0.4],
            [0.8, 0.4],
            [0.8, 0.8],
            [0.0, 0.8]
        ]
        # Point inside base of L
        assert point_in_polygon((0.2, 0.2), poly) is True
        # Point inside right arm of L
        assert point_in_polygon((0.6, 0.6), poly) is True
        # Point in the cut-out corner of the L
        assert point_in_polygon((0.6, 0.2), poly) is False

    def test_degenerate_polygons(self):
        assert point_in_polygon((0.5, 0.5), []) is False
        assert point_in_polygon((0.5, 0.5), [[0.1, 0.1], [0.2, 0.2]]) is False


class TestZoneManagerAndState:
    """Tests ZoneManager and WorkstationState 5-minute debounce."""

    def test_zone_manager_matching(self):
        mgr = ZoneManager(zones_file=None)
        z1 = ZoneCreate(
            zone_id="ZONE-DESK-A",
            camera_id="CAM-01",
            name="Desk A",
            zone_type="WORKSTATION",
            capacity=1,
            polygon_coords=[[0.1, 0.1], [0.4, 0.1], [0.4, 0.4], [0.1, 0.4]]
        )
        z2 = ZoneCreate(
            zone_id="ZONE-CORRIDOR",
            camera_id="CAM-01",
            name="Corridor",
            zone_type="CORRIDOR",
            capacity=10,
            polygon_coords=[[0.5, 0.1], [0.9, 0.1], [0.9, 0.9], [0.5, 0.9]]
        )
        mgr.add_zone(z1)
        mgr.add_zone(z2)

        matched_desk = mgr.match_zone((0.25, 0.25), "CAM-01")
        assert matched_desk == "ZONE-DESK-A"

        matched_corr = mgr.match_zone((0.7, 0.5), "CAM-01")
        assert matched_corr == "ZONE-CORRIDOR"


        matched_outside = mgr.match_zone((0.05, 0.05), "CAM-01")
        assert matched_outside is None

    def test_workstation_state_transitory_debounce(self):
        state = WorkstationState(zone_id="ZONE-POD-1", debounce_seconds=300.0)
        assert state.state == "VACANT"

        # Occupant arrives at time t0
        t0 = 1000.0
        s1 = state.update(is_occupied=True, current_time=t0, active_track_hash="TRK-001")
        assert s1 == "OCCUPIED"
        assert state.state == "OCCUPIED"

        # Occupant steps away for 120 seconds (coffee break, transitory departure)
        t1 = t0 + 120.0
        s2 = state.update(is_occupied=False, current_time=t1)
        # Should stay OCCUPIED due to 300-second debounce
        assert s2 == "OCCUPIED"

        # Occupant still absent after 301 seconds
        t2 = t1 + 301.0
        s3 = state.update(is_occupied=False, current_time=t2)
        # Debounce expired -> State transitions to VACANT
        assert s3 == "VACANT"
        assert state.total_vacant_seconds > 0.0

