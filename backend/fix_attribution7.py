import re
with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'r') as f:
    c = f.read()

c = c.replace('''            if track_id:
                seg.participant_track_id = track_id
                attributed_count += 1
                
            evidence_rows.append(AttributionEvidence(
                segment_id=seg.id,
                                participant_track_id=track_id,
                details={"method": "mouth_activity_90p"},
                                score=1.0, rank=1
            ))''', '''            if track_id:
                seg.participant_track_id = track_id
                attributed_count += 1
                
                evidence_rows.append(AttributionEvidence(
                    segment_id=seg.id,
                    participant_track_id=track_id,
                    details={"method": "mouth_activity_90p"},
                    score=1.0, rank=1
                ))''')

with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'w') as f:
    f.write(c)
