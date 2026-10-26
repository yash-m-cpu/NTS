import re
with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'r') as f:
    c = f.read()

c = c.replace('scores=attr["evidence"].get("scores", {}),\n', '')
c = c.replace('chosen_reason=attr["evidence"].get("method", "unknown")\n', 'score=1.0, rank=1\n')

with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'w') as f:
    f.write(c)
