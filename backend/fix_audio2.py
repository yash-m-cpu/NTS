with open('c:/PJT/backend/app/workers/audio_preprocess_worker.py', 'r') as f:
    c = f.read()
c = c.replace('upload_status="completed"', 'upload_status="uploaded"')
with open('c:/PJT/backend/app/workers/audio_preprocess_worker.py', 'w') as f:
    f.write(c)
