import re
with open('c:/PJT/backend/app/workers/listener_analysis_worker.py', 'r') as f:
    c = f.read()

c = c.replace(
    'listener_track_id=listener_id,',
    'participant_track_id=listener_id,'
)
c = c.replace(
    'speaker_track_id=speaker_id,',
    'target_track_id=speaker_id,\n                            state="listening",\n                            derivation="heuristic",'
)

with open('c:/PJT/backend/app/workers/listener_analysis_worker.py', 'w') as f:
    f.write(c)
