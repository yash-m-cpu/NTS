import re
with open('c:/PJT/backend/app/services/speech/attribution.py', 'r') as f:
    c = f.read()

c = c.replace('a.mouth_open_ratio', 'a.mar')

with open('c:/PJT/backend/app/services/speech/attribution.py', 'w') as f:
    f.write(c)
