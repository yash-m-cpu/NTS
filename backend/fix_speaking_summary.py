import re
with open('c:/PJT/backend/app/api/v1/meetings.py', 'r') as f:
    c = f.read()

c = c.replace(
    'metric_dict = {m.metric_key: m.value for m in metrics}',
    'metric_dict = {m.metric_key: float(m.value) if m.value is not None else None for m in metrics}'
)

with open('c:/PJT/backend/app/api/v1/meetings.py', 'w') as f:
    f.write(c)
