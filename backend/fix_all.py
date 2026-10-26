import glob

for fpath in glob.glob('c:/PJT/backend/app/workers/*.py'):
    with open(fpath, 'r') as f:
        c = f.read()
    if 'audio_16k' in c:
        c = c.replace("asset_type == 'audio_16k'", "asset_type == 'audio'")
        c = c.replace('asset_type == "audio_16k"', 'asset_type == "audio"')
        c = c.replace('No audio_16k media asset found', 'No audio media asset found')
        # Keep audio_16k.wav in the key if we want, it doesn't hurt.
        with open(fpath, 'w') as f:
            f.write(c)
        print(f"Fixed {fpath}")
