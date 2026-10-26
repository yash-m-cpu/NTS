import asyncio
import logging
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.features import FeatureExtraction
from app.models.jobs import ProcessingJob
from app.models.media import MediaAsset
from app.models.participants import ParticipantTrack

logger = logging.getLogger(__name__)

# Color palette per participant (BGR format for OpenCV)
PARTICIPANT_COLORS = [
    (52, 152, 219),   # blue
    (231, 76, 60),    # red
    (46, 204, 113),   # green
    (155, 89, 182),   # purple
    (230, 126, 34),   # orange
    (26, 188, 156),   # teal
    (241, 196, 15),   # yellow
    (236, 240, 241),  # light gray
]

# MediaPipe BlazePose connections (33 keypoints, 0-indexed)
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),     # face left
    (0, 4), (4, 5), (5, 6), (6, 8),     # face right
    (9, 10),                              # mouth
    (11, 12),                             # shoulders
    (11, 13), (13, 15),                  # left arm
    (12, 14), (14, 16),                  # right arm
    (11, 23), (12, 24), (23, 24),        # torso
    (23, 25), (25, 27), (27, 29), (29, 31), (27, 31),  # left leg
    (24, 26), (26, 28), (28, 30), (30, 32), (28, 32),  # right leg
]


def _get_color(track_index: int) -> tuple:
    return PARTICIPANT_COLORS[track_index % len(PARTICIPANT_COLORS)]


def _draw_skeleton(frame, keypoints: list, color: tuple, width: int, height: int) -> None:
    """Draw posture skeleton on frame given normalized keypoints."""
    import cv2  # lazy import
    if not keypoints or len(keypoints) < 5:
        return
    
    # Convert normalized to pixel coords
    pts = {}
    for kp in keypoints:
        idx = kp.get("id", kp.get("part", len(pts)))
        if isinstance(idx, str):
            continue  # skip named parts
        
        x_val = kp.get("x") if kp.get("x") is not None else kp.get("xn", 0)
        y_val = kp.get("y") if kp.get("y") is not None else kp.get("yn", 0)
        
        x = int(x_val * width)
        y = int(y_val * height)
        score = kp.get("score", 1.0)
        pts[idx] = (x, y, score)
    
    # Draw connections
    for (i, j) in POSE_CONNECTIONS:
        if i in pts and j in pts:
            x1, y1, s1 = pts[i]
            x2, y2, s2 = pts[j]
            if s1 > 0.3 and s2 > 0.3:
                cv2.line(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
    
    # Draw joints
    for idx, (x, y, score) in pts.items():
        if score > 0.3:
            cv2.circle(frame, (x, y), 4, color, -1, cv2.LINE_AA)
            cv2.circle(frame, (x, y), 4, (255, 255, 255), 1, cv2.LINE_AA)


def _draw_participant(
    frame,
    track_label: str,
    track_index: int,
    face_features: list,
    pose_features: list,
    hand_features: list,
    emotion_features: list,
    width: int,
    height: int,
) -> None:
    """Draw all overlays for a single participant on a single frame."""
    import cv2  # lazy import
    color = _get_color(track_index)
    dark_color = tuple(max(0, c - 60) for c in color)

    # Track highest point to draw the label consistently above the head
    highest_y = height
    leftmost_x = width // 2
    found_points = False

    # --- Face bounding box ---
    if face_features:
        box = None
        for ff in face_features:
            vals = ff.get("values", {})
            if "box" in vals:
                box = vals["box"]
                break
        
        if box:
            try:
                if box and len(box) == 4:
                    x, y, w, h = box
                    if x is not None and y is not None and w is not None and h is not None:
                        if x <= 1.0 and y <= 1.0:  # normalized
                            x, y, w, h = int(x * width), int(y * height), int(w * width), int(h * height)
                        else:
                            x, y, w, h = int(x), int(y), int(w), int(h)
                        
                        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2, cv2.LINE_AA)
                        
                        if y < highest_y:
                            highest_y = y
                            leftmost_x = x
                            found_points = True
            except Exception:
                pass

    # --- Pose skeleton ---
    if pose_features:
        for pf in pose_features:
            vals = pf.get("values", {})
            kps = vals.get("keypoints", [])
            if kps:
                _draw_skeleton(frame, kps, color, width, height)
                # Use keypoints to find the highest point (head) if no face box
                for kp in kps:
                    px_val = kp.get("x") if kp.get("x") is not None else kp.get("xn", 0)
                    py_val = kp.get("y") if kp.get("y") is not None else kp.get("yn", 0)
                    score = kp.get("score", 1.0)
                    if score > 0.2:
                        px = int(px_val * width)
                        py = int(py_val * height)
                        if py < highest_y:
                            highest_y = py
                            leftmost_x = px - 20 # Offset slightly so it's centered over head
                            found_points = True
                break

    # --- Draw prominent participant label above the head ---
    if found_points:
        label = track_label
        # Make the font slightly larger and thicker for visibility
        font_scale = 0.6
        thickness = 2
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        
        # Calculate box coordinates above highest_y
        box_y2 = max(0, highest_y - 8)
        box_y1 = max(0, box_y2 - label_size[1] - 10)
        box_x1 = max(0, leftmost_x)
        box_x2 = min(width, box_x1 + label_size[0] + 10)
        
        # Draw solid background for the text
        cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), color, -1)
        # Draw white border around the label
        cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), (255, 255, 255), 1, cv2.LINE_AA)
        
        text_x = box_x1 + 5
        text_y = box_y2 - 5
        cv2.putText(frame, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    # --- Head rotation overlay (yaw/pitch/roll text) ---
    if face_features:
        for ff in face_features:
            vals = ff.get("values", {})
            rot = vals.get("rotation", {})
            if rot:
                yaw = rot.get("yaw", 0)
                pitch = rot.get("pitch", 0)
                roll = rot.get("roll", 0)
                rot_text = f"Y:{yaw:.2f} P:{pitch:.2f} R:{roll:.2f}"
                txt_y = 30 + track_index * 75
                cv2.rectangle(frame, (10, txt_y - 18), (280, txt_y + 10), (0, 0, 0), -1)
                cv2.putText(frame, f"[{track_label}]", (12, txt_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
                cv2.putText(frame, rot_text, (12, txt_y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (220, 220, 220), 1, cv2.LINE_AA)
                break

    # --- Dominant emotion overlay ---
    if emotion_features:
        for ef in emotion_features:
            vals = ef.get("values", {})
            dom = vals.get("dominant_emotion") or ""
            emotions = vals.get("emotions", {})
            if not dom and emotions:
                dom = max(emotions, key=emotions.get)
            if dom:
                emo_score = emotions.get(dom, 0)
                emo_text = f"{dom} ({emo_score:.0%})"
                txt_y = 30 + track_index * 75 + 22
                cv2.putText(frame, emo_text, (12, txt_y), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)
                break

    # --- Hand presence indicator ---
    if hand_features:
        for hf in hand_features:
            vals = hf.get("values", {})
            hands = vals.get("hands", [])
            if hands:
                hand_count = len(hands)
                ht = 30 + track_index * 75 + 38
                cv2.putText(frame, f"Hands: {hand_count}", (12, ht), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)
                break



def _build_frame_index(all_features: list, tracks: list) -> dict:
    """
    Build a per-frame lookup dict:
    frame_ms -> { track_id -> { feature_type -> [feature_dict] } }
    We bucket features into 500ms windows for approximate frame lookup.
    """
    BUCKET_MS = 500

    index = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    track_id_to_index = {str(t.id): i for i, t in enumerate(tracks)}
    
    for feat in all_features:
        bucket = (feat.timestamp_ms // BUCKET_MS) * BUCKET_MS
        index[bucket][str(feat.participant_track_id)][feat.feature_type].append({
            "timestamp_ms": feat.timestamp_ms,
            "values": feat.values or {},
            "confidence": float(feat.confidence) if feat.confidence else 0.0,
        })
    
    return index, track_id_to_index


def _render_video(
    input_path: str,
    output_path: str,
    frame_index: dict,
    track_id_to_index: dict,
    tracks: list,
) -> bool:
    """
    Read the video frame-by-frame, draw annotations, stream directly to ffmpeg to get web-compatible H.264.
    Returns True on success.
    """
    import cv2
    import numpy as np
    import subprocess
    import shutil

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", input_path)
        return False
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    logger.info("Rendering annotated video: %dx%d @ %.1f fps, %d frames", width, height, fps, total_frames)
    
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-", # read from stdin
        "-i", input_path, # read audio from original video
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-map", "0:v:0", # Use video from stdin
        "-map", "1:a:0?", # Use audio from input_path (if exists)
        "-movflags", "+faststart",
        output_path
    ]
    
    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    
    BUCKET_MS = 500
    frame_number = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        timestamp_ms = int((frame_number / fps) * 1000)
        bucket_ms = (timestamp_ms // BUCKET_MS) * BUCKET_MS
        
        bucket_data = frame_index.get(bucket_ms, {})
        
        for track in tracks:
            track_id = str(track.id)
            track_index = track_id_to_index.get(track_id, 0)
            track_feats = bucket_data.get(track_id, {})
            
            _draw_participant(
                frame=frame,
                track_label=track.track_label,
                track_index=track_index,
                face_features=track_feats.get("face_pose", []) or track_feats.get("rotation", []),
                pose_features=track_feats.get("body_pose", []),
                hand_features=track_feats.get("hand_pose", []),
                emotion_features=track_feats.get("emotion", []),
                width=width,
                height=height,
            )
        
        # Timestamp watermark
        ts_str = f"{timestamp_ms // 60000:02d}:{(timestamp_ms % 60000) // 1000:02d}"
        cv2.putText(frame, f"NTS Analysis - {ts_str}", (width - 230, height - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
        
        ffmpeg_proc.stdin.write(frame.tobytes())
        frame_number += 1
        
        if frame_number % 100 == 0:
            logger.info("  Rendered %d / %d frames (%.0f%%)", frame_number, total_frames, 100 * frame_number / max(total_frames, 1))
    
    cap.release()
    ffmpeg_proc.stdin.close()
    
    # Read stderr asynchronously or just wait if we don't care about deadlock (since we only read at end).
    # But wait, to prevent deadlock, we should read stderr before wait if possible.
    # Actually, communicate() throws ValueError if stdin is closed. We can just wait.
    ffmpeg_proc.wait()
    stderr = ffmpeg_proc.stderr.read()
    
    if ffmpeg_proc.returncode != 0:
        logger.error(f"FFmpeg failed with code {ffmpeg_proc.returncode}")
        logger.error(f"FFmpeg stderr: {stderr.decode('utf-8', errors='ignore')}")
        return False
        
    logger.info("Render complete: %d frames", frame_number)
    return frame_number > 0


async def handle_video_annotation(ctx, db: AsyncSession, job_id: str, kwargs: dict):
    """
    ARQ handler for annotated_video_generation jobs.
    Downloads the original video, renders annotations from DB features, uploads result.
    """
    job = await db.scalar(select(ProcessingJob).where(ProcessingJob.id == UUID(job_id)))
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    logger.info("[VideoAnnotation] Starting job %s for meeting %s", job_id, job.meeting_id)
    
    # Resolve media asset
    asset = await db.scalar(
        select(MediaAsset)
        .where(MediaAsset.meeting_id == job.meeting_id)
        .order_by(MediaAsset.created_at.desc())
    )
    if not asset:
        raise ValueError(f"No media asset for meeting {job.meeting_id}")
    
    # Fetch all participant tracks for this meeting
    from app.models.jobs import ProcessingJob as PJ
    cv_job = await db.scalar(
        select(PJ)
        .where(PJ.meeting_id == job.meeting_id, PJ.job_type == "cv_extraction", PJ.status == "succeeded")
        .order_by(PJ.finished_at.desc())
    )
    
    if not cv_job:
        raise ValueError("CV extraction job has not completed yet. Cannot generate annotated video.")
    
    tracks_result = await db.execute(
        select(ParticipantTrack)
        .where(ParticipantTrack.processing_job_id == cv_job.id)
        .order_by(ParticipantTrack.track_label)
    )
    tracks = list(tracks_result.scalars().all())
    
    if not tracks:
        raise ValueError("No participant tracks found for this meeting.")
    
    track_ids = [t.id for t in tracks]
    
    # Fetch all feature extractions
    feats_result = await db.execute(
        select(FeatureExtraction)
        .where(FeatureExtraction.participant_track_id.in_(track_ids))
        .order_by(FeatureExtraction.timestamp_ms)
    )
    all_features = list(feats_result.scalars().all())
    logger.info("[VideoAnnotation] Loaded %d feature records for %d tracks", len(all_features), len(tracks))
    
    # Build frame index
    frame_index, track_id_to_index = _build_frame_index(all_features, tracks)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "original.mp4")
        output_path = os.path.join(tmpdir, "annotated.mp4")
        
        # Download original video
        logger.info("[VideoAnnotation] Downloading video: %s", asset.storage_key)
        import aioboto3
        session = aioboto3.Session()
        async with session.client(
            "s3",
            endpoint_url=settings.AWS_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME,
        ) as s3:
            await s3.download_file(settings.S3_BUCKET_NAME, asset.storage_key, input_path)
        
        logger.info("[VideoAnnotation] Downloaded %.1f MB. Rendering...", os.path.getsize(input_path) / (1024 * 1024))
        
        # Render in thread pool (CPU-bound)
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, _render_video, input_path, output_path, frame_index, track_id_to_index, tracks
        )
        
        if not success:
            raise ValueError("Video rendering produced no frames.")
        
        # Upload annotated video to MinIO
        annotated_key = f"annotated/{asset.storage_key}"
        logger.info("[VideoAnnotation] Uploading annotated video: %s", annotated_key)
        async with session.client(
            "s3",
            endpoint_url=settings.AWS_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME,
        ) as s3:
            await s3.upload_file(
                output_path,
                settings.S3_BUCKET_NAME,
                annotated_key,
                ExtraArgs={"ContentType": "video/mp4"},
            )
        
        # Update media asset with the new key
        asset.annotated_video_key = annotated_key
        await db.commit()
        
        logger.info("[VideoAnnotation] Done. Annotated video stored at %s", annotated_key)
        return {
            "annotated_video_key": annotated_key,
            "tracks": len(tracks),
            "features": len(all_features),
        }
