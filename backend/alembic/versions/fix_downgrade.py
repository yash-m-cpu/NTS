import re

with open('c:/PJT/backend/alembic/versions/7d4cb11dcc92_add_speech_schema.py', 'r') as f:
    content = f.read()

# Replace the entire downgrade function
new_downgrade = '''def downgrade() -> None:
    \"\"\"Downgrade schema.\"\"\"
    op.drop_column('meetings', 'speech_status')
    op.drop_column('media_assets', 'av_offset_ms')
    op.drop_column('media_assets', 'video_start_offset_ms')
    op.drop_column('media_assets', 'audio_start_offset_ms')
    op.drop_table('speech_words')
    op.drop_table('attribution_evidence')
    op.drop_table('track_speech_activity')
    op.drop_table('speech_segments')
    op.drop_table('speech_metrics')
    op.drop_table('prosody_windows')
    op.drop_table('mouth_activity')
    op.drop_table('listener_states')
    op.drop_table('interaction_events')
    op.drop_table('vad_segments')
    op.drop_table('diarization_turns')
    op.drop_table('speech_reports')
    op.drop_table('pipeline_runs')
'''

content = re.sub(r'def downgrade\(\) -> None:.*', new_downgrade, content, flags=re.DOTALL)

with open('c:/PJT/backend/alembic/versions/7d4cb11dcc92_add_speech_schema.py', 'w') as f:
    f.write(content)
