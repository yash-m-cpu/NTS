with open('c:/PJT/backend/app/workers/audio_preprocess_worker.py', 'r') as f:
    c = f.read()
c = c.replace('asset_type="audio_16k"', 'asset_type="audio"')
with open('c:/PJT/backend/app/workers/audio_preprocess_worker.py', 'w') as f:
    f.write(c)
