"""FastAPI backend application for WBPIS.

Implements RESTful contracts, live MJPEG streaming, WebSocket telemetry,
zone configuration management, scorecard calculation, and outcome webhooks.
"""

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
import cv2
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from src.analytics.recommendations import Recommendation, RecommendationEngine
from src.analytics.scorecards import ScorecardEngine
from src.core.config import settings
from src.core.logging import logger
from src.core.schemas import (
    LiveTelemetryMessage,
    OperationalOutcomeBatch,
    ScorecardSuite,
    ZoneCreate,
    ZoneRead
)
from src.export.video_exporter import VideoExportJob
from src.backend.pipeline import get_pipeline
from src.perception.spatial import WorkstationState
from src.storage.database import get_db, init_db
from src.storage.repository import TelemetryRepository

# Initialize database tables on app startup
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Asynchronous backend API for CCTV Workplace Productivity & Workflow Intelligence"
)

# Enable CORS for dashboard clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure exports directory exists and mount static route
settings.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/exports", StaticFiles(directory=str(settings.EXPORT_DIR)), name="exports")

# In-memory export jobs registry
export_jobs: Dict[str, VideoExportJob] = {}



# ============================================================================
# 1. SYSTEM HEALTH & SESSION ENDPOINTS
# ============================================================================

@app.get("/health", tags=["System"])
def health_check() -> Dict[str, Any]:
    """Returns application health and configuration metadata."""
    return {
        "status": "HEALTHY",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "detector_initialized": True,
        "database_backend": "SQLite" if settings.DATABASE_URL.startswith("sqlite") else "PostgreSQL/TimescaleDB"
    }


@app.get("/api/v1/system/audit-logs", tags=["System"])
def get_audit_logs(limit: int = 50, db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Returns recent security and privacy audit logs."""
    logs = TelemetryRepository.get_recent_audit_logs(db, limit=limit)
    return [
        {
            "log_id": log.log_id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "user_id": log.user_id,
            "user_role": log.user_role,
            "action_type": log.action_type,
            "resource_id": log.resource_id,
            "client_ip": log.client_ip,
            "status_code": log.status_code,
            "details": log.details
        }
        for log in logs
    ]



@app.post("/api/v1/sessions/start", tags=["Session"])
def start_session(camera_id: str = "CAM-01") -> Dict[str, Any]:
    """Starts perception pipeline worker for a specified camera."""
    pipeline = get_pipeline(camera_id)
    pipeline.start()
    return {
        "status": "STREAMING",
        "camera_id": camera_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "stream_url": f"/api/v1/stream/live/{camera_id}"
    }


@app.post("/api/v1/sessions/stop", tags=["Session"])
def stop_session(camera_id: str = "CAM-01") -> Dict[str, Any]:
    """Stops perception pipeline worker for a specified camera."""
    pipeline = get_pipeline(camera_id)
    pipeline.stop()
    return {
        "status": "STOPPED",
        "camera_id": camera_id,
        "stopped_at": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/v1/sessions/status/{camera_id}", tags=["Session"])
def get_session_status(camera_id: str = "CAM-01") -> Dict[str, Any]:
    """Returns current FPS, dropped frames, active tracks, and health status."""
    pipeline = get_pipeline(camera_id)
    return {
        "camera_id": camera_id,
        "is_alive": pipeline.ingest_worker.is_connected,
        "fps": round(pipeline.latest_fps, 1),
        "active_tracks_count": len(pipeline.latest_tracks),
        "total_frames_processed": pipeline.ingest_worker.frames_processed,
        "dropped_frames_count": pipeline.ingest_worker.mailbox.dropped_frames,
        "observation_coverage_pct": 100.0 if pipeline.ingest_worker.is_connected else 0.0
    }


@app.post("/api/v1/videos/upload", status_code=status.HTTP_201_CREATED, tags=["Session"])
async def upload_video(
    file: UploadFile = File(...),
    camera_id: str = "CAM-01",
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Uploads a video file and dynamically binds it to the specified camera perception pipeline."""
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    clean_name = f"{int(time.time())}_{file.filename}"
    target_path = settings.UPLOAD_DIR / clean_name

    contents = await file.read()
    with open(target_path, "wb") as f:
        f.write(contents)

    pipeline = get_pipeline(camera_id)
    pipeline.set_source(target_path, restart=True)

    TelemetryRepository.log_audit(
        db=db,
        user_id="operator",
        user_role="OPERATOR",
        action_type="VIDEO_UPLOAD",
        resource_id=f"{camera_id}:{clean_name}",
        payload={"filename": file.filename, "size_bytes": len(contents)}
    )

    return {
        "status": "UPLOADED",
        "filename": file.filename,
        "saved_path": str(target_path),
        "camera_id": camera_id,
        "is_streaming": True,
        "size_bytes": len(contents)
    }



# ============================================================================
# 2. LIVE VIDEO STREAMING & WEBSOCKETS (REMEDIATION OF BUG-01)
# ============================================================================

async def mjpeg_generator(camera_id: str):
    """Yields multipart JPEG frames for browser streaming without blocking workers."""
    pipeline = get_pipeline(camera_id)
    while True:
        jpeg_bytes = pipeline.get_annotated_jpeg()
        if jpeg_bytes is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
            )
        await asyncio.sleep(0.04)  # ~25 FPS max stream output


@app.get("/api/v1/stream/live/{camera_id}", tags=["Streaming"])
async def stream_live_video(camera_id: str = "CAM-01") -> StreamingResponse:
    """Streams live annotated video preview over MJPEG multipart format."""
    return StreamingResponse(
        mjpeg_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws/live-telemetry/{camera_id}")
async def websocket_live_telemetry(websocket: WebSocket, camera_id: str = "CAM-01") -> None:
    """Asynchronous WebSocket streaming real-time track telemetry at 5 Hz."""
    await websocket.accept()
    pipeline = get_pipeline(camera_id)
    logger.info(f"WebSocket client connected to /ws/live-telemetry/{camera_id}")

    try:
        while True:
            snapshot = pipeline.get_live_telemetry_snapshot()
            await websocket.send_text(snapshot.model_dump_json())
            await asyncio.sleep(0.20)  # 5 Hz broadcast rate
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from /ws/live-telemetry/{camera_id}")
    except Exception as e:
        logger.error(f"WebSocket telemetry error on {camera_id}: {e}")


@app.get("/api/v1/telemetry/live/{camera_id}", response_model=LiveTelemetryMessage, tags=["Streaming"])
def get_live_telemetry(camera_id: str = "CAM-01") -> LiveTelemetryMessage:
    """Returns the latest live telemetry snapshot including all active tracks and metrics."""
    pipeline = get_pipeline(camera_id)
    return pipeline.get_live_telemetry_snapshot()


# ============================================================================
# 3. SPATIAL ZONE CONFIGURATION ENDPOINTS
# ============================================================================

@app.get("/api/v1/zones", response_model=List[ZoneRead], tags=["Zones"])
def list_zones(camera_id: Optional[str] = None) -> List[ZoneRead]:
    """Lists registered spatial zones filtered by camera ID."""
    pipeline = get_pipeline(camera_id or "CAM-01")
    return pipeline.zone_mgr.list_zones(camera_id)


@app.post("/api/v1/zones", response_model=ZoneRead, status_code=status.HTTP_201_CREATED, tags=["Zones"])
def create_or_update_zone(zone_def: ZoneCreate, db: Session = Depends(get_db)) -> ZoneRead:
    """Registers or updates a spatial region of interest polygon."""
    pipeline = get_pipeline(zone_def.camera_id)
    zone = pipeline.zone_mgr.add_zone(zone_def)
    pipeline.zone_mgr.save_zones()

    # Re-initialize zone state machine
    pipeline.workstation_states[zone.zone_id] = pipeline.workstation_states.get(
        zone.zone_id, WorkstationState(zone.zone_id)
    )

    TelemetryRepository.log_audit(
        db=db,
        user_id="facility_manager",
        user_role="FACILITY_MANAGER",
        action_type="ZONE_UPSERT",
        resource_id=zone.zone_id,
        payload=zone_def.model_dump()
    )
    return zone


@app.delete("/api/v1/zones/{zone_id}", tags=["Zones"])
def delete_zone(zone_id: str, camera_id: str = "CAM-01", db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Deletes a registered zone."""
    pipeline = get_pipeline(camera_id)
    removed = pipeline.zone_mgr.remove_zone(zone_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found.")
    pipeline.zone_mgr.save_zones()
    if zone_id in pipeline.workstation_states:
        del pipeline.workstation_states[zone_id]

    TelemetryRepository.log_audit(
        db=db,
        user_id="facility_manager",
        user_role="FACILITY_MANAGER",
        action_type="ZONE_DELETE",
        resource_id=zone_id
    )
    return {"status": "DELETED", "zone_id": zone_id}


# ============================================================================
# 4. ANALYTICS & SCORECARDS ENDPOINTS
# ============================================================================

@app.get("/api/v1/analytics/scorecards", response_model=ScorecardSuite, tags=["Analytics"])
def get_scorecards(
    camera_id: str = "CAM-01",
    department: str = "ENG",
    db: Session = Depends(get_db)
) -> ScorecardSuite:
    """Assembles and returns the four decoupled Scorecards (A, B, C, D)."""
    pipeline = get_pipeline(camera_id)

    # 1. Scorecard A arguments
    sc_a_args = {
        "interruption_events": 1,
        "focus_hours": 1.0,
        "waiting_seconds": 60.0,
        "operational_seconds": 3600.0,
        "congested_seconds": 30.0,
        "monitored_seconds": 3600.0,
        "transitions_count": 4,
        "monitored_hours": 1.0
    }

    # 2. Scorecard B arguments
    activity_dist = pipeline.get_activity_distribution()
    sc_b_args = {
        "activity_shares": activity_dist,
        "interaction_ratio_pct": 58.0,
        "movement_ratio_pct": 8.0,
        "transition_rate": 6.2,
        "unknown_ratio_pct": activity_dist.get("ACT-07", 0.0)
    }

    # 3. Scorecard C arguments
    rolling_wor = pipeline.get_rolling_wor()
    sc_c_args = {
        "occupied_seconds": rolling_wor * 36.0,
        "monitored_seconds": 3600.0,
        "total_presence_seconds": rolling_wor * 36.0,
        "away_time_ratio_pct": max(0.0, 100.0 - rolling_wor)
    }

    # 4. Scorecard D: Query latest external outcomes from database
    latest_outcome = TelemetryRepository.get_latest_outcomes(db, department)
    sc_d_args = {}
    if latest_outcome:
        sc_d_args = {
            "actual_units": latest_outcome.actual_output,
            "target_units": latest_outcome.target_output,
            "accepted_units": int(latest_outcome.actual_output * (latest_outcome.quality_rate_pct / 100.0)),
            "assessed_units": latest_outcome.actual_output,
            "on_time_units": int(latest_outcome.actual_output * (latest_outcome.timeliness_rate_pct / 100.0)),
            "total_deadline_units": latest_outcome.actual_output
        }

    return ScorecardEngine.build_suite(
        camera_id=camera_id,
        scorecard_a_args=sc_a_args,
        scorecard_b_args=sc_b_args,
        scorecard_c_args=sc_c_args,
        scorecard_d_args=sc_d_args
    )


@app.get("/api/v1/analytics/recommendations", response_model=List[Recommendation], tags=["Analytics"])
def get_recommendations(camera_id: str = "CAM-01") -> List[Recommendation]:
    """Returns deterministic layout recommendations based on Rules REC-01 to REC-04."""
    pipeline = get_pipeline(camera_id)
    wor = pipeline.get_rolling_wor()

    return RecommendationEngine.evaluate(
        wor_pct=wor,
        sru_pct=72.0,
        waiting_ratio_pct=4.2,
        interruption_freq=1.5,
        repeated_trip_rate=1.2,
        observation_coverage_pct=100.0
    )


@app.get("/api/v1/analytics/hourly-metrics", tags=["Analytics"])
def get_hourly_metrics(
    zone_id: Optional[str] = None,
    limit: int = 24,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Returns recent aggregated hourly metrics."""
    metrics = TelemetryRepository.get_recent_hourly_metrics(db, zone_id=zone_id, limit=limit)
    return [
        {
            "id": m.id,
            "hour_bucket": m.hour_bucket.isoformat() if m.hour_bucket else None,
            "zone_id": m.zone_id,
            "occupancy_rate_pct": m.occupancy_rate_pct,
            "interaction_ratio_pct": m.interaction_ratio_pct,
            "transition_count": m.transition_count,
            "interruption_count": m.interruption_count,
            "observation_coverage_pct": m.observation_coverage_pct
        }
        for m in metrics
    ]



# ============================================================================
# 5. EXTERNAL OPERATIONAL OUTCOME INGESTION WEBHOOK
# ============================================================================

@app.post("/api/v1/ingest/operational-outcomes", status_code=status.HTTP_202_ACCEPTED, tags=["Integration"])
def ingest_operational_outcomes(
    batch: OperationalOutcomeBatch,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Ingests verified business outcome records from Jira, SAP, or ticketing webhooks."""
    outcome = TelemetryRepository.record_operational_outcomes(db, batch)
    TelemetryRepository.log_audit(
        db=db,
        user_id="enterprise_webhook",
        user_role="SYSTEM_INTEGRATION",
        action_type="OUTCOME_INGEST",
        resource_id=f"{batch.department_code}:{batch.report_date}",
        payload=batch.model_dump()
    )
    return {
        "status": "ACCEPTED",
        "report_date": outcome.report_date,
        "department_code": outcome.department_code,
        "output_effectiveness_score": outcome.output_effectiveness_score,
        "derived_metrics": {
            "quality_rate_pct": outcome.quality_rate_pct,
            "timeliness_rate_pct": outcome.timeliness_rate_pct,
            "rework_rate_pct": outcome.rework_rate_pct
        }
    }


# ============================================================================
# 6. ASYNCHRONOUS MP4 EXPORT ENDPOINTS
# ============================================================================

@app.post("/api/v1/export/video", status_code=status.HTTP_202_ACCEPTED, tags=["Export"])
def trigger_video_export(
    camera_id: str = "CAM-01",
    max_frames: int = 150,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Triggers an asynchronous annotated MP4 video clip export."""
    job_id = f"EXP-{int(time.time())}"
    source = settings.SAMPLE_VIDEO_PATH or Path("sample.mp4")
    out_path = settings.EXPORT_DIR / f"{job_id}_{camera_id}.mp4"

    job = VideoExportJob(
        job_id=job_id,
        source_path=source,
        output_path=out_path,
        camera_id=camera_id,
        max_frames=max_frames
    )
    export_jobs[job_id] = job
    job.start_async()

    TelemetryRepository.log_audit(
        db=db,
        user_id="facility_manager",
        user_role="FACILITY_MANAGER",
        action_type="EXPORT_TRIGGERED",
        resource_id=job_id
    )

    return {
        "job_id": job_id,
        "status": "QUEUED",
        "output_filename": out_path.name
    }


@app.get("/api/v1/export/status/{job_id}", tags=["Export"])
def get_export_status(job_id: str) -> Dict[str, Any]:
    """Polls the rendering progress of an active export job."""
    job = export_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Export job '{job_id}' not found.")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress_pct": job.progress_pct,
        "frames_rendered": job.frames_rendered,
        "total_frames": job.total_frames,
        "error_message": job.error_message,
        "download_url": f"/exports/{job.output_path.name}" if job.status == "READY" else None
    }


# ============================================================================
# 7. PRODUCTION FRONTEND SERVING (REACT SPA)
# ============================================================================
frontend_dist = settings.BASE_DIR / "frontend" / "dist"
if (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="react-assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_react_app(full_path: str):
    """Serves the production React SPA for non-API frontend routes with deep-linking."""
    if full_path.startswith(("api/", "health", "ws/", "exports/", "docs", "redoc", "openapi.json")):
        raise HTTPException(status_code=404, detail="API route not found.")

    file_path = frontend_dist / full_path
    if file_path.is_file():
        return FileResponse(str(file_path))

    index_file = frontend_dist / "index.html"
    if index_file.is_file():
        return FileResponse(str(index_file))

    return JSONResponse(status_code=404, content={"detail": "Frontend assets not found."})

