import asyncio
import json
import logging
import os
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.jobs import ProcessingJob
from app.models.media import MediaAsset
from app.models.participants import ParticipantTrack
from app.models.features import FeatureExtraction
from app.models.models_registry import ModelVersion

logger = logging.getLogger(__name__)

CV_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "human_cv_script.js"

async def _get_or_create_model_version(db: AsyncSession, name: str, version: str) -> UUID:
    mv = await db.scalar(select(ModelVersion).where(ModelVersion.name == name, ModelVersion.version == version))
    if mv:
        return mv.id
    mv = ModelVersion(
        model_family="cv_extraction",
        name=name,
        version=version,
        artifact_uri=f"file://human-main/models",
        status="active",
    )
    db.add(mv)
    await db.flush()
    return mv.id

async def _download_from_minio(storage_key: str, dest_path: str) -> None:
    """Download a file from MinIO to a local temp path."""
    import aioboto3
    session = aioboto3.Session()
    async with session.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION_NAME,
    ) as s3:
        await s3.download_file(settings.S3_BUCKET_NAME, storage_key, dest_path)
    logger.info("Downloaded %s to %s", storage_key, dest_path)

def _run_human_script(video_path: str, sample_fps: int) -> list[dict]:
    """Run the Node.js human CV script synchronously, collect all JSON lines."""
    script_path = str(CV_SCRIPT)
    logger.info("Spawning Node.js CV script: %s fps=%d", video_path, sample_fps)
    
    env = os.environ.copy()
    
    proc = subprocess.run(
        ["node", script_path, video_path, str(sample_fps)],
        capture_output=True,
        text=True,
        timeout=600,  # 10 minute max
        env=env,
    )
    
    if proc.returncode != 0:
        logger.error("Node CV script stderr: %s", proc.stderr[-2000:])
        raise RuntimeError(f"human_cv_script.js failed with code {proc.returncode}")
    
    if proc.stderr:
        logger.debug("Node CV script stderr: %s", proc.stderr[-500:])
    
    results = []
    for line in proc.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Skipping non-JSON line: %s", line[:100])
    
    return results

def _aggregate_windows(frame_results: list[dict], sample_fps: int) -> dict:
    """
    Aggregate per-frame detections into 1-second windows per stable person identity.

    IMPORTANT — STABLE IDENTITY ASSIGNMENT:
    The JS `face.id` field from @vladmandic/human is UNSTABLE: when frames are
    dropped (because the model was still busy), the library resets its internal
    tracker and re-assigns IDs starting from 0. This causes person_0 and person_1
    to swap labels mid-video in the annotated output.

    Fix: Ignore face.id entirely. Instead, re-assign identities each frame by
    sorting detected faces left-to-right by their bounding-box X coordinate.
    The leftmost face is ALWAYS person_0; the next leftmost is person_1, etc.
    This is a robust spatial anchor — people in a meeting do not jump sides.
    """
    windows = defaultdict(lambda: defaultdict(list))

    for frame in frame_results:
        if frame.get("__summary__"):
            continue
        timestamp_ms = frame.get("timestamp_ms", 0)
        window_sec = timestamp_ms // 1000

        # ------------------------------------------------------------------
        # Step 1: Sort faces left-to-right by bounding box X coordinate.
        # box = [x, y, w, h] in normalised [0..1] coordinates.
        # ------------------------------------------------------------------
        faces_sorted = sorted(
            [f for f in frame.get("faces", []) if f.get("box") and f["box"][0] is not None],
            key=lambda f: f["box"][0]
        )

        bodies = frame.get("bodies", [])
        hands = frame.get("hands", [])

        # ------------------------------------------------------------------
        # Step 2: Associate bodies to faces by nearest X-centre proximity.
        # ------------------------------------------------------------------
        unmatched_bodies = list(bodies)
        body_by_pos_idx: dict[int, dict] = {}
        for pos_idx, face in enumerate(faces_sorted):
            fx = face["box"][0] + face["box"][2] / 2
            best_body = None
            best_dist = 0.20  # allow up to 20% frame width apart
            for b in unmatched_bodies:
                if not b.get("box"):
                    continue
                bx = b["box"][0] + b["box"][2] / 2
                dist = abs(bx - fx)
                if dist < best_dist:
                    best_dist = dist
                    best_body = b
            if best_body:
                body_by_pos_idx[pos_idx] = best_body
                unmatched_bodies.remove(best_body)

        # ------------------------------------------------------------------
        # Step 3: Associate hands to nearest face.
        # ------------------------------------------------------------------
        hands_by_pos_idx: dict[int, list] = defaultdict(list)
        for h in hands:
            if not h.get("box"):
                continue
            hx = h["box"][0] + h["box"][2] / 2
            nearest_idx = 0
            nearest_dist = float("inf")
            for pos_idx, face in enumerate(faces_sorted):
                fx = face["box"][0] + face["box"][2] / 2
                dist = abs(hx - fx)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = pos_idx
            hands_by_pos_idx[nearest_idx].append(h)

        # ------------------------------------------------------------------
        # Step 4: Build observation records keyed by stable positional label.
        # ------------------------------------------------------------------
        for pos_idx, face in enumerate(faces_sorted):
            person_id = f"person_{pos_idx}"
            body = body_by_pos_idx.get(pos_idx, {})
            person_hands = hands_by_pos_idx.get(pos_idx, [])

            scores = [s for s in [face.get("score"), body.get("score")] + [h.get("score") for h in person_hands] if s]
            score = max(scores) if scores else 0

            windows[person_id][window_sec].append({
                "timestamp_ms": timestamp_ms,
                "frame": frame.get("frame", 0),
                "score": score,
                "face_box": face.get("box"),
                "rotation": face.get("rotation"),
                "gaze": face.get("gaze"),
                "emotion": face.get("emotion", []),
                "body_box": body.get("box"),
                "body_keypoints": body.get("keypoints", []),
                "hands": person_hands
            })
    return dict(windows)

def _calc_window_features(observations: list[dict]) -> dict:
    """Calculate aggregated features for a 1-second window of observations."""
    if not observations:
        return {}
    
    features = {}
    valid_count = len(observations)
    
    # Head pose aggregation
    yaws = [o["rotation"]["yaw"] for o in observations if o.get("rotation") and "yaw" in o["rotation"]]
    pitches = [o["rotation"]["pitch"] for o in observations if o.get("rotation") and "pitch" in o["rotation"]]
    rolls = [o["rotation"]["roll"] for o in observations if o.get("rotation") and "roll" in o["rotation"]]
    
    if yaws:
        features["head_yaw_mean"] = sum(yaws) / len(yaws)
        features["head_yaw_std"] = (sum((y - features["head_yaw_mean"])**2 for y in yaws) / len(yaws)) ** 0.5
    if pitches:
        features["head_pitch_mean"] = sum(pitches) / len(pitches)
        features["head_pitch_std"] = (sum((p - features["head_pitch_mean"])**2 for p in pitches) / len(pitches)) ** 0.5
    if rolls:
        features["head_roll_mean"] = sum(rolls) / len(rolls)
    
    # Head motion magnitude
    if yaws and pitches:
        features["head_motion_magnitude"] = (features.get("head_yaw_std", 0)**2 + features.get("head_pitch_std", 0)**2) ** 0.5
    
    # Gaze aggregation
    bearings = [o["gaze"]["bearing"] for o in observations if o.get("gaze") and "bearing" in o["gaze"]]
    strengths = [o["gaze"]["strength"] for o in observations if o.get("gaze") and "strength" in o["gaze"]]
    if bearings:
        features["gaze_bearing_mean"] = sum(bearings) / len(bearings)
        features["gaze_stability"] = 1.0 - min(1.0, (sum((b - features["gaze_bearing_mean"])**2 for b in bearings) / len(bearings)) ** 0.5 / 3.14159)
    if strengths:
        features["gaze_strength_mean"] = sum(strengths) / len(strengths)
    
    # Emotion: dominant emotion per window
    emotion_totals = {}
    emotion_counts = {}
    for obs in observations:
        for e in obs.get("emotion", []):
            emotion_totals[e["emotion"]] = emotion_totals.get(e["emotion"], 0) + e["score"]
            emotion_counts[e["emotion"]] = emotion_counts.get(e["emotion"], 0) + 1
    if emotion_totals:
        features["emotion_distribution"] = {
            k: round(emotion_totals[k] / emotion_counts[k], 4)
            for k in emotion_totals
        }
        features["dominant_emotion"] = max(emotion_totals, key=emotion_totals.get)
        
    # Posture Stability & Gesture Activity
    # Simple metric: number of times hands appear, and variance in body box position
    body_xs = [o["body_box"][0] for o in observations if o.get("body_box") and isinstance(o["body_box"][0], (int, float))]
    if body_xs:
        mean_x = sum(body_xs) / len(body_xs)
        std_x = (sum((x - mean_x)**2 for x in body_xs) / len(body_xs)) ** 0.5
        features["posture_stability"] = max(0.0, 1.0 - std_x)  # simplified normalized stability
        
    hand_counts = [len(o.get("hands", [])) for o in observations]
    features["gesture_activity"] = sum(hand_counts) / len(hand_counts) if hand_counts else 0.0

    # Average detection confidence
    scores = [o["score"] for o in observations if o.get("score")]
    if scores:
        features["avg_detection_confidence"] = sum(scores) / len(scores)
    
    features["observation_count"] = valid_count
    
    return features

async def handle_cv_extraction(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job:
        raise ValueError("Job not found")
    
    logger.info("[CV] Starting job %s for meeting %s", job_id, job.meeting_id)
    
    # Resolve media asset
    media_asset_id = job.media_asset_id
    if not media_asset_id:
        asset = await db.scalar(
            select(MediaAsset)
            .where(MediaAsset.meeting_id == job.meeting_id)
            .order_by(MediaAsset.created_at.desc())
        )
        if not asset:
            raise ValueError(f"No media asset for meeting {job.meeting_id}. Upload a file first.")
        media_asset_id = asset.id
        storage_key = asset.storage_key
    else:
        asset = await db.scalar(select(MediaAsset).where(MediaAsset.id == media_asset_id))
        if not asset:
            raise ValueError(f"MediaAsset {media_asset_id} not found")
        storage_key = asset.storage_key
    
    # Resolve model version
    model_version_id = job.model_version_id or await _get_or_create_model_version(
        db, name="human-cv", version="human@3+tfjs@4"
    )
    
    sample_fps = settings.CV_FRAME_SAMPLE_RATE
    logger.info("[CV] Downloading video: %s", storage_key)
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # Download video from MinIO
        await _download_from_minio(storage_key, tmp_path)
        
        file_size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
        logger.info("[CV] Downloaded %.1f MB. Running human CV at %d fps sample rate", file_size_mb, sample_fps)
        
        # Run Node.js CV script (synchronous, runs in thread pool to avoid blocking event loop)
        loop = asyncio.get_event_loop()
        frame_results = await loop.run_in_executor(
            None, _run_human_script, tmp_path, sample_fps
        )
        
        # Extract summary
        summary = next((r for r in frame_results if r.get("__summary__")), {})
        frame_results = [r for r in frame_results if not r.get("__summary__")]
        
        total_frames = summary.get("total_frames", len(frame_results))
        duration_ms = summary.get("duration_ms", 0)
        video_fps = summary.get("video_fps", 0)
        
        logger.info("[CV] Processed %d frames. Duration: %dms @ %.1f fps. Aggregating...", 
                    total_frames, duration_ms, video_fps)
        
        # Aggregate per-person windows
        person_windows = _aggregate_windows(frame_results, sample_fps)
        
        # Calculate per-person stats
        person_stats = {}
        for person_id, windows in person_windows.items():
            total_observations = sum(len(obs) for obs in windows.values())
            total_possible = total_frames  # max possible is num frames sampled
            person_stats[person_id] = {
                "observation_count": total_observations,
                "visibility_pct": round(min(100.0, total_observations / max(total_frames, 1) * 100), 1),
                "window_count": len(windows),
            }
            logger.info("[CV]   %s: %d observations, %.1f%% visibility",
                        person_id, total_observations, person_stats[person_id]["visibility_pct"])
        
        # Persist to database
        tracks_created = 0
        features_created = 0
        
        from sqlalchemy import delete
        # Remove any existing visual tracks for this media asset to prevent duplicate/orphan tracks
        await db.execute(
            delete(ParticipantTrack).where(
                ParticipantTrack.media_asset_id == media_asset_id,
                ParticipantTrack.track_label.like("person_%")
            )
        )
        await db.flush()
        
        for person_id, windows in person_windows.items():
            all_frames = [obs for obs_list in windows.values() for obs in obs_list]
            timestamps = [obs["timestamp_ms"] for obs in all_frames]
            first_ms = min(timestamps) if timestamps else 0
            last_ms = max(timestamps) if timestamps else 0
            avg_confidence = sum(obs["score"] for obs in all_frames) / len(all_frames) if all_frames else 0
            
            track = ParticipantTrack(
                organization_id=job.organization_id,
                media_asset_id=media_asset_id,
                processing_job_id=job.id,
                track_label=person_id,
                first_seen_at_ms=first_ms,
                last_seen_at_ms=last_ms,
                detection_frame_count=len(all_frames),
                avg_detection_confidence=round(avg_confidence, 4),
            )
            db.add(track)
            await db.flush()
            tracks_created += 1
            
            # Per-frame features
            for obs in all_frames:
                frame_idx = obs["frame"]
                ts_ms = obs["timestamp_ms"]
                score = round(obs.get("score", 0), 4)
                
                if obs.get("rotation") or obs.get("face_box"):
                    rot = obs.get("rotation", {})
                    db.add(FeatureExtraction(
                        organization_id=job.organization_id, participant_track_id=track.id, media_asset_id=media_asset_id, processing_job_id=job.id,
                        model_version_id=model_version_id, extraction_pipeline_version="human-cv@3", feature_type="face_pose", timestamp_ms=ts_ms, frame_index=frame_idx, confidence=score,
                        values={
                            "rotation": {"yaw": round(rot.get("yaw", 0), 4), "pitch": round(rot.get("pitch", 0), 4), "roll": round(rot.get("roll", 0), 4)} if rot else {},
                            "box": obs.get("face_box")
                        }
                    ))
                    features_created += 1
                    
                if obs.get("gaze"):
                    db.add(FeatureExtraction(
                        organization_id=job.organization_id, participant_track_id=track.id, media_asset_id=media_asset_id, processing_job_id=job.id,
                        model_version_id=model_version_id, extraction_pipeline_version="human-cv@3", feature_type="gaze", timestamp_ms=ts_ms, frame_index=frame_idx, confidence=score,
                        values={"gaze": obs["gaze"]}
                    ))
                    features_created += 1
                
                if obs.get("emotion"):
                    db.add(FeatureExtraction(
                        organization_id=job.organization_id, participant_track_id=track.id, media_asset_id=media_asset_id, processing_job_id=job.id,
                        model_version_id=model_version_id, extraction_pipeline_version="human-cv@3", feature_type="emotion", timestamp_ms=ts_ms, frame_index=frame_idx, confidence=score,
                        values={"emotions": {e["emotion"]: round(e["score"], 4) for e in obs["emotion"]}}
                    ))
                    features_created += 1
                    
                if obs.get("body_keypoints"):
                    db.add(FeatureExtraction(
                        organization_id=job.organization_id, participant_track_id=track.id, media_asset_id=media_asset_id, processing_job_id=job.id,
                        model_version_id=model_version_id, extraction_pipeline_version="human-cv@3", feature_type="body_pose", timestamp_ms=ts_ms, frame_index=frame_idx, confidence=score,
                        values={"keypoints": obs["body_keypoints"]}
                    ))
                    features_created += 1
                    
                if obs.get("hands"):
                    db.add(FeatureExtraction(
                        organization_id=job.organization_id, participant_track_id=track.id, media_asset_id=media_asset_id, processing_job_id=job.id,
                        model_version_id=model_version_id, extraction_pipeline_version="human-cv@3", feature_type="hand_pose", timestamp_ms=ts_ms, frame_index=frame_idx, confidence=score,
                        values={"hands": obs["hands"]}
                    ))
                    features_created += 1
                
                if obs.get("emotion"):
                    db.add(FeatureExtraction(
                        organization_id=job.organization_id,
                        participant_track_id=track.id,
                        media_asset_id=media_asset_id,
                        processing_job_id=job.id,
                        model_version_id=model_version_id,
                        extraction_pipeline_version="human-cv@3",
                        feature_type="emotion",
                        timestamp_ms=ts_ms,
                        frame_index=frame_idx,
                        confidence=round(obs.get("score", 0), 4),
                        values={"emotions": {e["emotion"]: round(e["score"], 4) for e in obs["emotion"]}},
                    ))
                    features_created += 1
            
            # Per-window aggregated features
            for window_sec, obs_list in windows.items():
                window_feats = _calc_window_features(obs_list)
                if not window_feats:
                    continue
                window_start_ms = window_sec * 1000
                window_end_ms = window_start_ms + 1000
                
                db.add(FeatureExtraction(
                    organization_id=job.organization_id,
                    participant_track_id=track.id,
                    media_asset_id=media_asset_id,
                    processing_job_id=job.id,
                    model_version_id=model_version_id,
                    extraction_pipeline_version="human-cv@3",
                    feature_type="gesture",  # windowed temporal aggregation (posture/gaze/emotion summary per 1s)
                    timestamp_ms=window_start_ms,
                    frame_index=None,
                    confidence=round(window_feats.get("avg_detection_confidence", 0), 4),
                    values={
                        "window_start_ms": window_start_ms,
                        "window_end_ms": window_end_ms,
                        "aggregated": True,
                        "head_yaw_mean": window_feats.get("head_yaw_mean"),
                        "head_yaw_std": window_feats.get("head_yaw_std"),
                        "head_pitch_mean": window_feats.get("head_pitch_mean"),
                        "head_pitch_std": window_feats.get("head_pitch_std"),
                        "head_roll_mean": window_feats.get("head_roll_mean"),
                        "head_motion_magnitude": window_feats.get("head_motion_magnitude"),
                        "gaze_bearing_mean": window_feats.get("gaze_bearing_mean"),
                        "gaze_stability": window_feats.get("gaze_stability"),
                        "emotion_distribution": window_feats.get("emotion_distribution"),
                        "dominant_emotion": window_feats.get("dominant_emotion"),
                        "posture_stability": window_feats.get("posture_stability"),
                        "gesture_activity": window_feats.get("gesture_activity"),
                    },
                ))
                features_created += 1
        
        await db.commit()
        
        logger.info("[CV] Complete. Tracks: %d, Features: %d", tracks_created, features_created)
        
        return {
            "tracks_created": tracks_created,
            "features_extracted": features_created,
            "participants_detected": len(person_windows),
            "total_frames_processed": total_frames,
            "duration_ms": duration_ms,
            "person_stats": person_stats,
        }
    
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
