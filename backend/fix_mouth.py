import re
with open('c:/PJT/backend/app/workers/mouth_activity_worker.py', 'r') as f:
    c = f.read()

c = c.replace('timestamp_ms=res["timestamp_ms"]', 't_ms=res["timestamp_ms"]')
c = c.replace("timestamp_ms=res['timestamp_ms']", "t_ms=res['timestamp_ms']")

with open('c:/PJT/backend/app/workers/mouth_activity_worker.py', 'w') as f:
    f.write(c)
