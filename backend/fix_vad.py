import re
with open('c:/PJT/backend/app/services/speech/vad.py', 'r') as f:
    c = f.read()

c = c.replace('timestamps = get_speech_timestamps(wav_path, model, vad_parameters=options)', 'timestamps = get_speech_timestamps(wav_path, vad_options=options)')
with open('c:/PJT/backend/app/services/speech/vad.py', 'w') as f:
    f.write(c)
