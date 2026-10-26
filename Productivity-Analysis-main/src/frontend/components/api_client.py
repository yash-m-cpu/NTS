"""HTTP API client for communicating with the WBPIS FastAPI backend."""

import os
from typing import Any, Dict, List, Optional
import requests


class WBPISApiClient:
    """Client for backend REST endpoints."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or os.getenv("WBPIS_BACKEND_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.timeout = 5.0

    def get_health(self) -> Optional[Dict[str, Any]]:
        """Checks backend health status."""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_session_status(self, camera_id: str = "CAM-01") -> Optional[Dict[str, Any]]:
        """Queries streaming worker telemetry for a camera."""
        try:
            resp = requests.get(f"{self.base_url}/api/v1/sessions/status/{camera_id}", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_live_telemetry(self, camera_id: str = "CAM-01") -> Optional[Dict[str, Any]]:
        """Queries current live tracks, bounding boxes, and personal metrics."""
        try:
            resp = requests.get(f"{self.base_url}/api/v1/telemetry/live/{camera_id}", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def start_session(self, camera_id: str = "CAM-01") -> Optional[Dict[str, Any]]:
        """Starts perception pipeline worker."""
        try:
            resp = requests.post(f"{self.base_url}/api/v1/sessions/start?camera_id={camera_id}", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def stop_session(self, camera_id: str = "CAM-01") -> Optional[Dict[str, Any]]:
        """Stops perception pipeline worker."""
        try:
            resp = requests.post(f"{self.base_url}/api/v1/sessions/stop?camera_id={camera_id}", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_stream_url(self, camera_id: str = "CAM-01") -> str:
        """Returns the MJPEG live video stream URL."""
        return f"{self.base_url}/api/v1/stream/live/{camera_id}"

    def upload_video(self, file_bytes: bytes, filename: str, camera_id: str = "CAM-01") -> Optional[Dict[str, Any]]:
        """Uploads a video file to the backend to set it as the active analysis feed."""
        try:
            files = {"file": (filename, file_bytes, "video/mp4")}
            resp = requests.post(
                f"{self.base_url}/api/v1/videos/upload?camera_id={camera_id}",
                files=files,
                timeout=60.0
            )
            if resp.status_code in (200, 201):
                return resp.json()
        except Exception:
            pass
        return None


    def get_zones(self, camera_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetches registered spatial zones."""
        try:
            url = f"{self.base_url}/api/v1/zones"
            if camera_id:
                url += f"?camera_id={camera_id}"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def create_zone(self, zone_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Registers or updates a spatial zone."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/zones",
                json=zone_payload,
                timeout=self.timeout
            )
            if resp.status_code in (200, 201):
                return resp.json()
        except Exception:
            pass
        return None

    def delete_zone(self, zone_id: str, camera_id: str = "CAM-01") -> bool:
        """Deletes a spatial zone."""
        try:
            resp = requests.delete(
                f"{self.base_url}/api/v1/zones/{zone_id}?camera_id={camera_id}",
                timeout=self.timeout
            )
            return resp.status_code == 200
        except Exception:
            return False

    def get_scorecards(self, camera_id: str = "CAM-01", department: str = "ENG") -> Optional[Dict[str, Any]]:
        """Fetches Scorecards A, B, C, D."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/analytics/scorecards?camera_id={camera_id}&department={department}",
                timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_recommendations(self, camera_id: str = "CAM-01") -> List[Dict[str, Any]]:
        """Fetches deterministic recommendations."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/analytics/recommendations?camera_id={camera_id}",
                timeout=self.timeout
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def ingest_operational_outcomes(self, outcome_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Posts external verified operational outcome records."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/ingest/operational-outcomes",
                json=outcome_data,
                timeout=self.timeout
            )
            if resp.status_code in (200, 202):
                return resp.json()
        except Exception:
            pass
        return None

    def trigger_video_export(self, camera_id: str = "CAM-01", max_frames: int = 150) -> Optional[Dict[str, Any]]:
        """Triggers an asynchronous annotated MP4 video export."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/export/video?camera_id={camera_id}&max_frames={max_frames}",
                timeout=self.timeout
            )
            if resp.status_code in (200, 202):
                return resp.json()
        except Exception:
            pass
        return None

    def get_export_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Polls progress of an active export job."""
        try:
            resp = requests.get(f"{self.base_url}/api/v1/export/status/{job_id}", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches recent security and privacy audit logs."""
        try:
            resp = requests.get(f"{self.base_url}/api/v1/system/audit-logs?limit={limit}", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []

    def get_hourly_metrics(self, zone_id: Optional[str] = None, limit: int = 24) -> List[Dict[str, Any]]:
        """Fetches aggregated hourly metrics."""
        try:
            url = f"{self.base_url}/api/v1/analytics/hourly-metrics?limit={limit}"
            if zone_id:
                url += f"&zone_id={zone_id}"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return []
