"""High-legibility visual overlay renderer with dynamic Level-of-Detail (LOD).

Renders person bounding boxes, ephemeral track handles, activity badges,
polygon zone perimeters, ground footprints, and timestamp headers.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from src.core.schemas import (
    Point2D,
    TrackObservation,
    ZoneRead,
    ZoneType
)


class OverlayRenderer:
    """Renders anti-aliased telemetry overlays directly onto OpenCV BGR frames."""

    # Color palette (BGR format)
    COLOR_WORKSTATION = (0, 200, 100)      # Emerald green
    COLOR_CORRIDOR = (0, 180, 255)         # Warm amber
    COLOR_SHARED = (255, 180, 0)           # Sky cyan
    COLOR_COMMON = (180, 180, 180)        # Neutral gray
    COLOR_TRACK_BOX = (255, 255, 255)      # White
    COLOR_FOOTPRINT = (0, 0, 255)          # Bright red
    COLOR_BANNER_BG = (20, 20, 20)         # Near-black
    COLOR_TEXT = (255, 255, 255)           # White

    def __init__(
        self,
        show_zones: bool = True,
        show_tracks: bool = True,
        show_metrics: bool = True,
        show_header: bool = True
    ):
        self.show_zones = show_zones
        self.show_tracks = show_tracks
        self.show_metrics = show_metrics
        self.show_header = show_header

    def render(
        self,
        frame: np.ndarray,
        tracks: List[TrackObservation],
        zones: List[ZoneRead],
        camera_id: str = "CAM-01",
        fps: float = 15.0,
        rolling_wor_pct: Optional[float] = None
    ) -> np.ndarray:
        """Renders all enabled telemetry layers onto a copy of the frame."""
        if frame is None or frame.size == 0:
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        out = frame.copy()
        h, w = out.shape[:2]

        # 1. Render Polygon Zones
        if self.show_zones and zones:
            self._render_zones(out, zones, w, h)

        # 2. Render Active Person Tracks
        if self.show_tracks and tracks:
            # Dynamic LOD: use compact mode when >= 5 people to avoid visual crowding
            use_compact_lod = len(tracks) >= 5
            for track in tracks:
                self._render_track(out, track, w, h, use_compact_lod)

        # 3. Render Top Telemetry Banner
        if self.show_header:
            self._render_header_banner(out, camera_id, fps, len(tracks), rolling_wor_pct, w, h)

        return out

    def _render_zones(self, img: np.ndarray, zones: List[ZoneRead], w: int, h: int) -> None:
        """Draws semi-transparent polygon regions and zone labels."""
        overlay = img.copy()

        for zone in zones:
            pts = np.array(
                [[int(pt[0] * w), int(pt[1] * h)] for pt in zone.polygon_normalized],
                dtype=np.int32
            )
            color = self._get_zone_color(zone.zone_type)

            # Draw filled polygon on overlay
            cv2.fillPoly(overlay, [pts], color)
            # Draw solid polygon boundary on main image
            cv2.polylines(img, [pts], isClosed=True, color=color, thickness=2, lineType=cv2.LINE_AA)

            # Zone label at polygon top-left
            min_x = int(min(pt[0] * w for pt in zone.polygon_normalized))
            min_y = int(min(pt[1] * h for pt in zone.polygon_normalized))
            label = f"{zone.name} ({zone.zone_type.value[:4]})"
            cv2.putText(
                img,
                label,
                (max(10, min_x + 5), max(20, min_y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA
            )

        # Blend semi-transparent fill (15% opacity)
        cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)

    def _render_track(
        self,
        img: np.ndarray,
        track: TrackObservation,
        w: int,
        h: int,
        compact_lod: bool
    ) -> None:
        """Renders bounding box, footprint, and informational pills for a track."""
        b = track.box
        x1, y1 = int(b.x1 * w), int(b.y1 * h)
        x2, y2 = int(b.x2 * w), int(b.y2 * h)

        # Draw bounding box
        box_color = (0, 255, 128) if track.current_zone_id else (255, 200, 0)
        cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 2, cv2.LINE_AA)

        # Draw ground-plane footprint point marker (X)
        fx, fy = int(track.footprint.x * w), int(track.footprint.y * h)
        cv2.drawMarker(img, (fx, fy), self.COLOR_FOOTPRINT, markerType=cv2.MARKER_CROSS, markerSize=12, thickness=2)

        # Level of Detail Rendering
        if compact_lod:
            # Compact LOD: Minimal top pill: [TRK-xxxx | Activity]
            label = f"{track.ephemeral_hash} | {track.activity_code.value.split(':')[0]}"
            self._draw_text_badge(img, label, x1, max(15, y1 - 8), font_scale=0.40, bg_color=(30, 30, 30))
        else:
            # Full LOD Card: Multi-line badge
            card_lines = [
                f"{track.ephemeral_hash} ({track.tracking_state.value[:4]})",
                f"Zone: {track.current_zone_id or 'In Walkway'}",
                f"{track.activity_code.value.split(':')[0]}",
                f"Conf: {int(track.detection_confidence * 100)}%"
            ]
            badge_y = max(60, y1 - 10)
            for idx, line in enumerate(reversed(card_lines)):
                self._draw_text_badge(
                    img,
                    line,
                    x1,
                    badge_y - (idx * 16),
                    font_scale=0.38,
                    bg_color=(25, 25, 25),
                    text_color=(240, 240, 240)
                )

    def _render_header_banner(
        self,
        img: np.ndarray,
        camera_id: str,
        fps: float,
        track_count: int,
        rolling_wor_pct: Optional[float],
        w: int,
        h: int
    ) -> None:
        """Renders top dark telemetry status strip."""
        cv2.rectangle(img, (0, 0), (w, 32), self.COLOR_BANNER_BG, -1)

        utc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        wor_str = f"WOR: {rolling_wor_pct:.1f}%" if rolling_wor_pct is not None else "WOR: N/A"

        header_text = f"[{camera_id}]  {utc_time}  |  FPS: {fps:.1f}  |  Active Tracks: {track_count}  |  {wor_str}  |  Privacy: Ephemeral Hashed"
        cv2.putText(
            img,
            header_text,
            (12, 21),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (220, 220, 220),
            1,
            cv2.LINE_AA
        )

    def _draw_text_badge(
        self,
        img: np.ndarray,
        text: str,
        x: int,
        y: int,
        font_scale: float = 0.40,
        bg_color: Tuple[int, int, int] = (20, 20, 20),
        text_color: Tuple[int, int, int] = (255, 255, 255)
    ) -> None:
        """Helper to draw text with an opaque background rectangle for maximum legibility."""
        (text_w, text_h), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        pad = 3
        cv2.rectangle(
            img,
            (x - pad, y - text_h - pad),
            (x + text_w + pad, y + pad),
            bg_color,
            -1
        )
        cv2.putText(
            img,
            text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            text_color,
            1,
            cv2.LINE_AA
        )

    def _get_zone_color(self, zone_type: ZoneType) -> Tuple[int, int, int]:
        if zone_type == ZoneType.WORKSTATION:
            return self.COLOR_WORKSTATION
        elif zone_type == ZoneType.CORRIDOR:
            return self.COLOR_CORRIDOR
        elif zone_type == ZoneType.SHARED_RESOURCE:
            return self.COLOR_SHARED
        return self.COLOR_COMMON
