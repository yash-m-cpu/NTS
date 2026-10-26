import re
with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'r') as f:
    c = f.read()

c = c.replace('run_id=run.id,\n', '')
c = c.replace('run_id=run.id, ', '')

with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'w') as f:
    f.write(c)
