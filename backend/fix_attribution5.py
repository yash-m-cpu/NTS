import re
with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'r') as f:
    c = f.read()

c = c.replace('scores=attr["scores"],', 'details={"scores": attr["scores"]},')

with open('c:/PJT/backend/app/workers/speaker_attribution_worker.py', 'w') as f:
    f.write(c)
