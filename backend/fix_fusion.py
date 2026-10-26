import re
with open('c:/PJT/backend/app/workers/feature_fusion_worker.py', 'r') as f:
    c = f.read()

c = c.replace('metric_category="interaction"', 'metric_category="temporal"')

with open('c:/PJT/backend/app/workers/feature_fusion_worker.py', 'w') as f:
    f.write(c)
