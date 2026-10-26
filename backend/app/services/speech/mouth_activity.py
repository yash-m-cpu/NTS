import math
import logging

import cv2
import mediapipe as mp

logger = logging.getLogger(__name__)

def compute_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def extract_mouth_activity_from_video(video_path: str, tracks_bboxes: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """
    Given a video path and a dictionary of track_id -> list of {"frame": int, "box": [x, y, w, h], "timestamp_ms": int},
    extracts the mouth open ratio for each frame using MediaPipe FaceMesh.
    Returns: dict of track_id -> list of {"timestamp_ms": int, "mouth_open_ratio": float}
    """
    logger.info(f"Extracting mouth activity for {len(tracks_bboxes)} tracks")
    
    mp_face_mesh = mp.solutions.face_mesh
    
    track_meshes = {}
    for track_id in tracks_bboxes.keys():
        track_meshes[track_id] = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
    frames_to_process = {}
    for track_id, bboxes in tracks_bboxes.items():
        for b in bboxes:
            frame_idx = b["frame"]
            if frame_idx not in frames_to_process:
                frames_to_process[frame_idx] = []
            frames_to_process[frame_idx].append({
                "track_id": track_id,
                "box": b["box"],
                "timestamp_ms": b["timestamp_ms"]
            })
            
    if not frames_to_process:
        return {}
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video {video_path}")
        
    results = {track_id: [] for track_id in tracks_bboxes.keys()}
    
    current_frame = 0
    max_frame = max(frames_to_process.keys())
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if current_frame in frames_to_process:
            h_img, w_img, _ = frame.shape
            
            for item in frames_to_process[current_frame]:
                track_id = item["track_id"]
                box = item["box"]
                ts_ms = item["timestamp_ms"]
                
                mor = 0.0
                
                if box and len(box) == 4:
                    if max(box) <= 1.5:
                        x = int(box[0] * w_img)
                        y = int(box[1] * h_img)
                        w = int(box[2] * w_img)
                        h = int(box[3] * h_img)
                    else:
                        x, y, w, h = [int(v) for v in box]
                    
                    pad_x = int(w * 0.2)
                    pad_y = int(h * 0.2)
                    
                    x1 = max(0, x - pad_x)
                    y1 = max(0, y - pad_y)
                    x2 = min(w_img, x + w + pad_x)
                    y2 = min(h_img, y + h + pad_y)
                    
                    crop = frame[y1:y2, x1:x2]
                    if crop.size > 0:
                        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                        mesh_result = track_meshes[track_id].process(crop_rgb)
                        
                        if mesh_result.multi_face_landmarks:
                            landmarks = mesh_result.multi_face_landmarks[0].landmark
                            
                            if len(landmarks) > 308:
                                upper = landmarks[13]
                                lower = landmarks[14]
                                left = landmarks[78]
                                right = landmarks[308]
                                
                                vert_dist = compute_distance(upper, lower)
                                horz_dist = compute_distance(left, right)
                                
                                if horz_dist > 0:
                                    mor = vert_dist / horz_dist
                                    
                results[track_id].append({
                    "timestamp_ms": ts_ms,
                    "mouth_open_ratio": mor
                })
                
        current_frame += 1
        if current_frame > max_frame:
            break
            
    cap.release()
    
    for mesh in track_meshes.values():
        mesh.close()
        
    return results
