import re
with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'r') as f:
    c = f.read()

c = c.replace('method="mouth_activity_90p",\n', 'details={"method": "mouth_activity_90p"},\n')
c = c.replace('method="mouth_activity_90p",', 'details={"method": "mouth_activity_90p"},')

with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'w') as f:
    f.write(c)
