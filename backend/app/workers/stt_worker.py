import os
import tempfile
import hashlib
import json
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import MediaAsset
from app.models.jobs import ProcessingJob
from app.models.participants import ParticipantTrack
from app.models.features import FeatureExtraction
from app.models.models_registry import ModelVersion
from app.models.speech import PipelineRun, SpeechSegment, SpeechWord, VadSegment
from app.services.storage_service import get_s3_client
from app.services.stt_service import stt_service
from app.services.diarization_service import diarization_service
from app.services.speaker_turns import align_stt_with_diarization

async def _get_or_create_model_version(db: AsyncSession, name: str, version: str) -> UUID:
    mv = await db.scalar(select(ModelVersion).where(ModelVersion.name == name, ModelVersion.version == version))
    if mv:
        return mv.id
    mv = ModelVersion(
        model_family="cv_extraction",
        name=name,
        version=version,
        artifact_uri=f"local://faster-whisper",
        status="active",
    )
    db.add(mv)
    await db.flush()
    return mv.id

async def handle_stt_transcription(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job or not job.media_asset_id:
        raise ValueError("Job not found or missing media_asset_id")

    asset = await db.scalar(
        select(MediaAsset)
        .where(MediaAsset.meeting_id == job.meeting_id)
        .where(MediaAsset.asset_type == 'audio')
        .order_by(MediaAsset.created_at.desc())
    )
    if not asset:
        # Fallback to the original video asset if audio preprocessing hasn't run
        asset = await db.scalar(select(MediaAsset).where(MediaAsset.id == job.media_asset_id))
        
    if not asset:
        raise ValueError("Media asset not found")

    model_version_id = job.model_version_id or await _get_or_create_model_version(db, name="faster-whisper", version="tiny")

    # Idempotency check for the new pipeline run (Phase 5)
    params = {"model_version_id": str(model_version_id)}
    params_hash = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    
    # We load VAD runs to include as input_run_ids
    vad_run = await db.scalar(
        select(PipelineRun)
        .where(PipelineRun.meeting_id == job.meeting_id)
        .where(PipelineRun.stage == "vad")
        .where(PipelineRun.status == "succeeded")
        .order_by(PipelineRun.finished_at.desc())
    )
    
    existing_run = await db.scalar(
        select(PipelineRun).where(
            PipelineRun.meeting_id == job.meeting_id,
            PipelineRun.stage == "stt_transcription",
            PipelineRun.params_hash == params_hash,
            PipelineRun.status == "succeeded"
        )
    )
    if existing_run:
        return {"run_id": str(existing_run.id), "status": "succeeded", "cached": True}

    run = PipelineRun(
        meeting_id=job.meeting_id,
        stage="stt_transcription",
        status="running",
        params=params,
        params_hash=params_hash,
        code_version="v1",
        model_versions={"faster-whisper": "tiny"},
        input_run_ids={"vad": str(vad_run.id) if vad_run else None},
        started_at=datetime.now(timezone.utc)
    )
    db.add(run)
    await db.flush()

    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = os.path.join(temp_dir, "audio.wav")
        
        # Download from S3
        async with get_s3_client() as s3:
            await s3.download_file(asset.storage_bucket, asset.storage_key, audio_path)

        # 1. Run STT
        segments = await stt_service.transcribe(audio_path)

        # 2. Run Diarization (Phase 6 cluster-lite)
        diarization = await diarization_service.diarize(audio_path)
        
        # --- PHASE 5 & 6: Write to new speech_segments and speech_words tables ---
        speech_segments_to_add = []
        speech_words_to_add = []
        
        for seg in segments:
            seg_start_ms = int(seg.start * 1000)
            seg_end_ms = int(seg.end * 1000)
            
            # Find dominant diarization cluster
            cluster_id = None
            max_overlap = 0
            for d in diarization:
                d_start = int(d["start"] * 1000)
                d_end = int(d["end"] * 1000)
                overlap = max(0, min(seg_end_ms, d_end) - max(seg_start_ms, d_start))
                if overlap > max_overlap:
                    max_overlap = overlap
                    cluster_id = d["speaker"].replace("speaker_", "cluster_")
            
            db_seg = SpeechSegment(
                meeting_id=job.meeting_id,
                run_id=run.id,
                start_ms=seg_start_ms,
                end_ms=seg_end_ms,
                text=seg.text,
                language="en",
                asr_avg_logprob=seg.avg_logprob,
                no_speech_prob=seg.no_speech_prob,
                diar_cluster_id=cluster_id,
                derivation="faster-whisper",
                evidence={"tokens": getattr(seg, "tokens", [])}
            )
            db.add(db_seg)
            await db.flush() # flush to get db_seg.id for words
            
            speech_segments_to_add.append(db_seg)
            
            if seg.words:
                for idx, w in enumerate(seg.words):
                    speech_words_to_add.append(SpeechWord(
                        segment_id=db_seg.id,
                        idx=idx,
                        start_ms=int(w.start * 1000),
                        end_ms=int(w.end * 1000),
                        word=w.word,
                        prob=w.probability
                    ))
                    
        if speech_words_to_add:
            db.add_all(speech_words_to_add)


        # --- PHASE 6 / BACKWARD COMPATIBILITY ---
        # Legacy mapping (writes to feature_extractions so UI does not break)
        turns = align_stt_with_diarization(segments, diarization)

        tracks_by_label = {}
        existing_tracks = await db.execute(
            select(ParticipantTrack).where(ParticipantTrack.media_asset_id == asset.id)
        )
        for t in existing_tracks.scalars().all():
            tracks_by_label[t.track_label] = t
            
        features = []
        speaker_track_map = {}
        
        for turn in turns:
            spk = turn.speaker
            if spk not in speaker_track_map:
                person_label = spk.replace("speaker_", "person_")
                
                if person_label in tracks_by_label:
                    track = tracks_by_label[person_label]
                elif spk in tracks_by_label:
                    track = tracks_by_label[spk]
                else:
                    track = ParticipantTrack(
                        organization_id=job.organization_id,
                        media_asset_id=asset.id,
                        processing_job_id=job.id,
                        track_label=spk,
                        first_seen_at_ms=int(turn.start * 1000),
                        last_seen_at_ms=int(turn.end * 1000)
                    )
                    db.add(track)
                    await db.flush()
                    tracks_by_label[spk] = track
                speaker_track_map[spk] = track
            
            track = speaker_track_map[spk]
            
            features.append(FeatureExtraction(
                organization_id=job.organization_id,
                participant_track_id=track.id,
                media_asset_id=asset.id,
                processing_job_id=job.id,
                model_version_id=model_version_id,
                extraction_pipeline_version="faster-whisper@tiny",
                feature_type="speaker_turn",
                timestamp_ms=int(turn.start * 1000),
                confidence=1.0,
                values={
                    "start": turn.start,
                    "end": turn.end,
                    "text": turn.text,
                    "words": [{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability} for w in getattr(turn, "words", [])]
                }
            ))

        if features:
            db.add_all(features)
            
        run.status = "succeeded"
        run.finished_at = datetime.now(timezone.utc)
        
        await db.commit()

        return {
            "run_id": str(run.id),
            "speech_segments": len(speech_segments_to_add),
            "speech_words": len(speech_words_to_add),
            "legacy_turns_extracted": len(turns)
        }
