"""Central configuration and settings for WBPIS."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def get_default_video_path() -> Optional[Path]:
    uploads_dir = BASE_DIR / "uploads"
    if uploads_dir.exists():
        vids = sorted(list(uploads_dir.glob("*.mp4")), key=lambda f: f.stat().st_mtime, reverse=True)
        for v in vids:
            if "office" in v.name.lower() or v.stat().st_size > 1_000_000:
                return v
    sample = (
        BASE_DIR / "audit_extracted" / "OpenCV-Based-Real-time-Employee-Tracking-System-main" /
        "uploads" / "1755331753_1755284023_Untitled_video_-_Made_with_Clipchamp.mp4"
    )
    return sample if sample.exists() else None


class Settings(BaseModel):
    """Application configuration settings loaded from environment or defaults."""

    # Project metadata
    PROJECT_NAME: str = "CCTV Workplace Productivity & Workflow Intelligence System"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("WBPIS_DEBUG", "false").lower() == "true"
    BASE_DIR: Path = BASE_DIR

    # Perception & Model configuration
    MODEL_DIR: Path = BASE_DIR / "audit_extracted" / "OpenCV-Based-Real-time-Employee-Tracking-System-main" / "yolo_model"
    YOLO_CFG_PATH: Path = MODEL_DIR / "yolov4-tiny.cfg"
    YOLO_WEIGHTS_PATH: Path = MODEL_DIR / "yolov4-tiny.weights"
    COCO_NAMES_PATH: Path = MODEL_DIR / "coco.names"

    SAMPLE_VIDEO_PATH: Optional[Path] = Field(default_factory=get_default_video_path)

    # Ingestion & Video parameters
    TARGET_FPS: float = float(os.getenv("WBPIS_TARGET_FPS", "15.0"))
    MAILBOX_MAXSIZE: int = int(os.getenv("WBPIS_MAILBOX_MAXSIZE", "2"))
    RTSP_TRANSPORT: str = os.getenv("WBPIS_RTSP_TRANSPORT", "tcp")
    CONFIDENCE_THRESHOLD: float = float(os.getenv("WBPIS_CONFIDENCE_THRESHOLD", "0.25"))
    NMS_THRESHOLD: float = float(os.getenv("WBPIS_NMS_THRESHOLD", "0.45"))
    INPUT_WIDTH: int = 416
    INPUT_HEIGHT: int = 416

    # Temporal & Spatial thresholds
    TRANSITORY_ABSENCE_GRACE_SECONDS: float = float(os.getenv("WBPIS_GRACE_SECONDS", "300.0"))  # 5 minutes
    INITIAL_OCCUPANCY_DEBOUNCE_SECONDS: float = 3.0  # 3 seconds to confirm presence
    ROLLING_METRIC_WINDOW_SECONDS: int = int(os.getenv("WBPIS_ROLLING_WINDOW_SECONDS", "300"))  # 5-minute rolling window
    MODAL_FILTER_WINDOW_FRAMES: int = 75             # 5.0s at 15 FPS

    # Workflow bottleneck thresholds
    CONGESTION_DENSITY_THRESHOLD: float = 0.50       # persons / m^2
    QUEUE_DWELL_MIN_SECONDS: float = 30.0            # stationary in queue zone
    INTERRUPTION_PROXIMITY_METERS: float = 1.5       # proximity boundary

    # Storage & Persistence
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./wbpis_telemetry.db")
    OUTPUT_FRAMES_DIR: Path = BASE_DIR / "output_frames"
    EXPORT_DIR: Path = BASE_DIR / "exports"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    LOGS_DIR: Path = BASE_DIR / "logs"
    RECORDING_RETENTION_HOURS: int = 72

    # Networking & Servers
    API_HOST: str = os.getenv("WBPIS_API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("WBPIS_API_PORT", "8001"))
    DASHBOARD_PORT: int = int(os.getenv("WBPIS_DASHBOARD_PORT", "8501"))
    SECRET_KEY: str = os.getenv("WBPIS_SECRET_KEY", "wbpis-default-insecure-secret-key-change-in-production")


settings = Settings()

# Ensure mandatory output directories exist
os.makedirs(settings.OUTPUT_FRAMES_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True)
os.makedirs(settings.LOGS_DIR, exist_ok=True)
