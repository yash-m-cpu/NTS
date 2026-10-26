from .registry import registry

@registry.register("gaze_aversion_ratio")
def compute_gaze_aversion_ratio(windows):
    gaze_windows = [w for w in windows if w.feature_type == "gaze"]
    if not gaze_windows:
        return None
        
    aversion_count = 0
    total_valid = 0
    for w in gaze_windows:
        agg = w.aggregation
        yaw = agg.get("yaw", 0)
        pitch = agg.get("pitch", 0)
        
        # Simplistic logic: if gaze is far from center, it's averted
        if abs(yaw) > 0.3 or abs(pitch) > 0.3:
            aversion_count += 1
        total_valid += 1
        
    if total_valid == 0:
        return None
        
    return {
        "value": aversion_count / total_valid,
        "category": "visual",
        "unit": "ratio"
    }
