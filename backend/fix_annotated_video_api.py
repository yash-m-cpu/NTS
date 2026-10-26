import re
with open('c:/PJT/backend/app/api/v1/meetings.py', 'r') as f:
    c = f.read()

c = c.replace(
    'select(MediaAsset).where(MediaAsset.meeting_id == id).order_by(MediaAsset.created_at.desc())',
    'select(MediaAsset).where(MediaAsset.meeting_id == id, MediaAsset.asset_type == "video").order_by(MediaAsset.created_at.desc())'
)

with open('c:/PJT/backend/app/api/v1/meetings.py', 'w') as f:
    f.write(c)
