import math
import logging

logger = logging.getLogger(__name__)

def target_direction(listener_bbox: list, speaker_bbox: list) -> float:
    """
    Given [x, y, w, h] for listener and speaker, approximate the angle 
    (in degrees) from listener to speaker in the 2D image plane.
    0 degrees is straight ahead (Z-axis). Positive is to the listener's right.
    (This is a rough heuristic given we lack 3D spatial positioning).
    """
    if not listener_bbox or not speaker_bbox:
        return 0.0
        
    lx_center = listener_bbox[0] + listener_bbox[2] / 2
    sx_center = speaker_bbox[0] + speaker_bbox[2] / 2
    
    # We map x-pixel difference to a rough bearing angle 
    # (Assuming FOV is roughly 90 degrees)
    # This is a very rough approximation.
    dx = sx_center - lx_center
    
    # Let's say listener width is ~0.5 meters, so we can establish a rough scale
    # But in radians: positive = right, negative = left
    # Let's just scale pixel distance into an angle
    # If the speaker is right of the listener, bearing is positive.
    
    # Very heuristic mapping: 1 screen width = 90 degrees
    # This needs the total image width, but we can just use relative difference
    # For now, let's just return an arbitrary angle proportional to dx.
    bearing_deg = dx * 0.1 # purely arbitrary scale without camera intrinsics
    return bearing_deg

def orientation_score(gaze: dict, head_rotation: dict, target_bearing_deg: float, tol_deg: float = 30.0) -> float:
    """
    Calculate how closely the listener's gaze/head aligns with the target bearing.
    Returns 0.0 to 1.0
    """
    # Gaze bearing is usually radians. 
    gaze_bearing_rad = gaze.get("bearing", 0.0) if gaze else 0.0
    gaze_bearing_deg = math.degrees(gaze_bearing_rad)
    
    head_yaw_rad = head_rotation.get("yaw", 0.0) if head_rotation else 0.0
    head_yaw_deg = math.degrees(head_yaw_rad)
    
    # Combine head and gaze (roughly)
    total_bearing = head_yaw_deg + gaze_bearing_deg
    
    diff = abs(total_bearing - target_bearing_deg)
    
    if diff <= tol_deg:
        return 1.0 - (diff / tol_deg)
    return 0.0

def gaze_on_target_pct(frames: list, window_s: float = 3.0, tol_deg: float = 30.0) -> float:
    """
    frames: list of dicts {"gaze": dict, "rotation": dict, "target_bearing": float}
    Returns percentage of frames where listener was looking at target.
    """
    if len(frames) < 15: # minimum valid frames
        return None
        
    on_target = 0
    
    for f in frames:
        score = orientation_score(f.get("gaze"), f.get("rotation"), f.get("target_bearing", 0.0), tol_deg)
        if score > 0.5:
            on_target += 1
            
    return on_target / len(frames)
