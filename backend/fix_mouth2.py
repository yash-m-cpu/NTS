import re
with open('c:/PJT/backend/app/workers/mouth_activity_worker.py', 'r') as f:
    c = f.read()

c = c.replace('timestamp_ms=act["timestamp_ms"],', 't_ms=act["timestamp_ms"],')
c = c.replace('mouth_open_ratio=act["mouth_open_ratio"]', 'mar=act["mouth_open_ratio"], visible=True')

with open('c:/PJT/backend/app/workers/mouth_activity_worker.py', 'w') as f:
    f.write(c)
