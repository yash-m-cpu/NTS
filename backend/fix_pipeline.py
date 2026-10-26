import glob

files = glob.glob('c:/PJT/backend/app/workers/*.py')
for f in files:
    with open(f, 'r') as file:
        content = file.read()
    
    if 'run = PipelineRun(' in content:
        if 'model_versions=' not in content:
            content = content.replace('code_version="v1",', 'code_version="v1",\n        model_versions={},')
            with open(f, 'w') as file:
                file.write(content)
            print(f'Fixed {f}')
