"""
API endpoints for NTS Visual Reports.
POST /meetings/{meeting_id}/tracks/{track_id}/report  — generate or return cached
GET  /meetings/{meeting_id}/tracks/{track_id}/report  — return structured JSON
GET  /meetings/{meeting_id}/tracks/{track_id}/report/pdf  — download PDF
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user, get_db
from app.core.config import settings
from app.models.users import User
from app.models.visual_reports import NtsVisualReport
from app.models.participants import ParticipantTrack
from app.services.visual_aggregator import build_visual_report_input, compute_input_hash
from app.services.llm_service import call_llm, PROMPT_VERSION
from app.services.pdf_generator import generate_and_upload_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["visual-reports"])


async def _get_track_or_404(db: AsyncSession, track_id: UUID, meeting_id: UUID) -> ParticipantTrack:
    from app.models.media import MediaAsset
    track = await db.scalar(
        select(ParticipantTrack)
        .join(MediaAsset, MediaAsset.id == ParticipantTrack.media_asset_id)
        .where(ParticipantTrack.id == track_id, MediaAsset.meeting_id == meeting_id)
    )
    if not track:
        raise HTTPException(status_code=404, detail="ParticipantTrack not found for this meeting")
    return track


async def _get_existing_report(
    db: AsyncSession, track_id: UUID, input_hash: str, prompt_version: str
) -> NtsVisualReport | None:
    return await db.scalar(
        select(NtsVisualReport).where(
            NtsVisualReport.participant_track_id == track_id,
            NtsVisualReport.input_hash == input_hash,
            NtsVisualReport.prompt_version == prompt_version,
            NtsVisualReport.status == "completed",
        )
    )


@router.post("/{meeting_id}/tracks/{track_id}/report", response_model=dict)
async def generate_report(
    meeting_id: UUID,
    track_id: UUID,
    force_regenerate: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
):
    """
    Generate or retrieve a cached NTS visual report for a participant track.
    Uses cached report if input_hash + prompt_version match.
    Set force_regenerate=true to bypass cache and regenerate.
    """
    track = await _get_track_or_404(db, track_id, meeting_id)

    # Build compact report input (no CV re-inference)
    try:
        report_input = await build_visual_report_input(db, track_id, meeting_id)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to aggregate visual data: {e}")

    input_hash = compute_input_hash(report_input)
    prompt_version = PROMPT_VERSION
    model_name = settings.LLM_MODEL

    # Check cache unless force_regenerate
    if not force_regenerate:
        cached = await _get_existing_report(db, track_id, input_hash, prompt_version)
        if cached:
            logger.info("Returning cached report %s for track %s", cached.id, track_id)
            return {"data": {
                "report_id": str(cached.id),
                "status": "completed",
                "cached": True,
                "report_json": cached.report_json,
                "pdf_available": cached.pdf_key is not None,
            }}

    # Check for ANY existing record with this hash
    existing_rec = await db.scalar(
        select(NtsVisualReport).where(
            NtsVisualReport.participant_track_id == track_id,
            NtsVisualReport.input_hash == input_hash,
            NtsVisualReport.prompt_version == prompt_version,
        )
    )

    if existing_rec:
        if existing_rec.status == "generating":
            return {"data": {"report_id": str(existing_rec.id), "status": "generating", "cached": False}}
        # If it's failed, or if we are force regenerating a completed one, just update it to generating
        existing_rec.status = "generating"
        existing_rec.error_message = None
        report_rec = existing_rec
    else:
        # Create new report record
        report_rec = NtsVisualReport(
            organization_id=track.organization_id,
            meeting_id=meeting_id,
            participant_track_id=track_id,
            input_hash=input_hash,
            prompt_version=prompt_version,
            model_name=model_name,
            status="generating",
        )
        db.add(report_rec)

    await db.commit()
    await db.refresh(report_rec)
    report_id = report_rec.id

    # Call LLM
    try:
        report_json = await call_llm(report_input)
    except ValueError as e:
        # Mark as failed — do not lose visual analysis
        report_rec.status = "failed"
        report_rec.error_message = str(e)[:500]
        await db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Report generation failed. Existing visual analysis is still available. Error: {e}",
        )

    # Generate PDF and upload to MinIO
    pdf_bucket, pdf_key = None, None
    try:
        pdf_bucket, pdf_key = await generate_and_upload_pdf(
            report_json, report_input, str(meeting_id), str(track_id)
        )
    except Exception as e:
        logger.warning("PDF generation failed (report JSON still saved): %s", e)

    # Save completed report
    report_rec.status = "completed"
    report_rec.report_json = report_json
    report_rec.pdf_bucket = pdf_bucket
    report_rec.pdf_key = pdf_key
    await db.commit()

    return {"data": {
        "report_id": str(report_id),
        "status": "completed",
        "cached": False,
        "report_json": report_json,
        "pdf_available": pdf_key is not None,
    }}


@router.get("/{meeting_id}/tracks/{track_id}/report", response_model=dict)
async def get_report(
    meeting_id: UUID,
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
):
    """Return the latest completed report JSON for a participant track."""
    await _get_track_or_404(db, track_id, meeting_id)

    rec = await db.scalar(
        select(NtsVisualReport).where(
            NtsVisualReport.participant_track_id == track_id,
            NtsVisualReport.meeting_id == meeting_id,
        ).order_by(NtsVisualReport.created_at.desc())
    )

    if not rec:
        raise HTTPException(status_code=404, detail="No report found for this participant")

    return {"data": {
        "report_id": str(rec.id),
        "status": rec.status,
        "report_json": rec.report_json,
        "pdf_available": rec.pdf_key is not None,
        "error_message": rec.error_message,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }}


@router.get("/{meeting_id}/tracks/{track_id}/report/pdf")
async def download_report_pdf(
    meeting_id: UUID,
    track_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
):
    """Download the PDF for a participant's report. Returns raw PDF bytes."""
    await _get_track_or_404(db, track_id, meeting_id)

    rec = await db.scalar(
        select(NtsVisualReport).where(
            NtsVisualReport.participant_track_id == track_id,
            NtsVisualReport.meeting_id == meeting_id,
            NtsVisualReport.status == "completed",
            NtsVisualReport.pdf_key.isnot(None),
        ).order_by(NtsVisualReport.created_at.desc())
    )

    if not rec or not rec.pdf_key:
        raise HTTPException(status_code=404, detail="No PDF available for this report")

    # Stream PDF from MinIO
    from app.services.storage_service import get_s3_client
    try:
        async with get_s3_client() as s3:
            obj = await s3.get_object(Bucket=rec.pdf_bucket, Key=rec.pdf_key)
            pdf_bytes = await obj["Body"].read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve PDF: {e}")

    track_label = (await db.scalar(select(ParticipantTrack).where(ParticipantTrack.id == track_id))).track_label
    filename = f"nts_report_{track_label}_{meeting_id}.pdf".replace(" ", "_")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
