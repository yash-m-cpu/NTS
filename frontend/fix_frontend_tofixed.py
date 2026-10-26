import re
with open('c:/PJT/frontend/src/routes/MeetingAnalysis.tsx', 'r') as f:
    c = f.read()

c = c.replace(
    "{selectedSpeech.avg_turn_duration_seconds ? selectedSpeech.avg_turn_duration_seconds.toFixed(1) + 's' : '0s'}",
    "{selectedSpeech.avg_turn_duration_seconds ? Number(selectedSpeech.avg_turn_duration_seconds).toFixed(1) + 's' : '0s'}"
)

with open('c:/PJT/frontend/src/routes/MeetingAnalysis.tsx', 'w') as f:
    f.write(c)
