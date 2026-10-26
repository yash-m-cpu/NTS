import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models_registry import ModelVersion
from app.models.jobs import ProcessingJob
from app.models.scores import NtsScore
from app.models.participants import ParticipantTrack

async def _get_or_create_model_version(db: AsyncSession, name: str, version: str) -> UUID:
    mv = await db.scalar(select(ModelVersion).where(ModelVersion.name == name, ModelVersion.version == version))
    if mv:
        return mv.id
    mv = ModelVersion(
        model_family="nts_scoring",
        name=name,
        version=version,
        artifact_uri=f"local://dummy-scorer",
        status="active",
    )
    db.add(mv)
    await db.flush()
    return mv.id

async def handle_nts_scoring(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job or not job.meeting_id:
        raise ValueError("Job not found or missing meeting_id")

    # Fetch participant tracks for this meeting
    result = await db.execute(select(ParticipantTrack).where(ParticipantTrack.media_asset_id == job.media_asset_id))
    tracks = result.scalars().all()

    model_version_id = job.model_version_id or await _get_or_create_model_version(db, "dummy-scorer", "1.0")

    # In a real scenario, we would load the scikit-learn model using job.model_version_id
    # and compute the features from behavioral_metrics for each track.
    
    scores = []
    for track in tracks:
        score = NtsScore(
            organization_id=job.organization_id,
            meeting_id=job.meeting_id,
            participant_track_id=track.id,
            model_version_id=model_version_id,
            processing_job_id=job.id,
            nts_score=85.0,  # Dummy score
            component_scores={"gaze": 90, "voice": 80}
        )
        scores.append(score)

    if scores:
        db.add_all(scores)
        await db.commit()
    
    return {"scored_tracks": len(scores)}
