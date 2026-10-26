import asyncio
import os
import sys

# Add the backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def seed_data():
    engine = create_async_engine(str(settings.DATABASE_URL), echo=True)
    async with engine.begin() as conn:
        # Example Records from 03_DATABASE_SCHEMA.md
        
        # Organizations and Users
        await conn.execute(text("""
            INSERT INTO organizations (id, name, slug) VALUES
              ('00000000-0000-0000-0000-000000000001', 'Acme Talent Solutions', 'acme-talent')
            ON CONFLICT DO NOTHING;
        """))
        
        await conn.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, status, email_verified_at) VALUES
              ('00000000-0000-0000-0000-000000000010', 'priya@acme-talent.com', '$argon2id$...', 'Priya Shah', 'active', now())
            ON CONFLICT DO NOTHING;
        """))
        
        await conn.execute(text("""
            INSERT INTO organization_members (organization_id, user_id, role) VALUES
              ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000010', 'ANALYST')
            ON CONFLICT DO NOTHING;
        """))
        
        # Projects and Meetings
        await conn.execute(text("""
            INSERT INTO projects (id, organization_id, name, created_by_user_id) VALUES
              ('00000000-0000-0000-0000-000000000020', '00000000-0000-0000-0000-000000000001',
               'Backend Interviews — Q3', '00000000-0000-0000-0000-000000000010')
            ON CONFLICT DO NOTHING;
        """))
        
        await conn.execute(text("""
            INSERT INTO meetings (id, organization_id, project_id, title, source_type, status, created_by_user_id) VALUES
              ('00000000-0000-0000-0000-000000000030', '00000000-0000-0000-0000-000000000001',
               '00000000-0000-0000-0000-000000000020', 'Candidate #482 — Round 2', 'upload', 'processing',
               '00000000-0000-0000-0000-000000000010')
            ON CONFLICT DO NOTHING;
        """))
        
        # Media Assets
        await conn.execute(text("""
            INSERT INTO media_assets (id, organization_id, meeting_id, asset_type, storage_bucket, storage_key,
                                       storage_provider, content_type, size_bytes, duration_seconds, upload_status)
            VALUES ('00000000-0000-0000-0000-000000000040', '00000000-0000-0000-0000-000000000001',
                    '00000000-0000-0000-0000-000000000030', 'video', 'nts-media-prod',
                    'orgs/acme-talent/meetings/0030/raw/session.mp4', 's3', 'video/mp4', 214748364, 1802.4, 'verified')
            ON CONFLICT DO NOTHING;
        """))
        
        # Model Versions
        await conn.execute(text("""
            INSERT INTO model_versions (id, model_family, name, version, status) VALUES
              ('00000000-0000-0000-0000-000000000050', 'cv_extraction', 'human-cv', '3.0.0', 'active'),
              ('00000000-0000-0000-0000-000000000051', 'nts_scoring', 'nts-gbm', '2026.08-a1', 'active')
            ON CONFLICT DO NOTHING;
        """))
        
        # Processing Jobs
        await conn.execute(text("""
            INSERT INTO processing_jobs (id, organization_id, meeting_id, media_asset_id, job_type, model_version_id, status)
            VALUES ('00000000-0000-0000-0000-000000000060', '00000000-0000-0000-0000-000000000001',
                    '00000000-0000-0000-0000-000000000030', '00000000-0000-0000-0000-000000000040',
                    'cv_extraction', '00000000-0000-0000-0000-000000000050', 'succeeded')
            ON CONFLICT DO NOTHING;
        """))
        
        # Participant Tracks
        await conn.execute(text("""
            INSERT INTO participant_tracks (id, organization_id, media_asset_id, processing_job_id, track_label,
                                             first_seen_at_ms, last_seen_at_ms, avg_detection_confidence)
            VALUES ('00000000-0000-0000-0000-000000000070', '00000000-0000-0000-0000-000000000001',
                    '00000000-0000-0000-0000-000000000040', '00000000-0000-0000-0000-000000000060',
                    'person_1', 0, 1802400, 0.9421)
            ON CONFLICT DO NOTHING;
        """))
        
        # Feature Extractions
        await conn.execute(text("""
            INSERT INTO feature_extractions (id, organization_id, participant_track_id, media_asset_id, processing_job_id,
                                              model_version_id, extraction_pipeline_version, feature_type, timestamp_ms,
                                              frame_index, confidence, values)
            VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000070',
                    '00000000-0000-0000-0000-000000000040', '00000000-0000-0000-0000-000000000060',
                    '00000000-0000-0000-0000-000000000050', 'human-cv@3.0.0+cfg-a7c1', 'gaze', 12500, 375, 0.88,
                    '{"direction":{"yaw":-4.2,"pitch":1.1}, "on_screen": true}'::jsonb)
            ON CONFLICT DO NOTHING;
        """))
        
        # Behavioral Metrics
        await conn.execute(text("""
            INSERT INTO behavioral_metrics (id, organization_id, participant_track_id, metric_key, metric_category,
                                             value, unit, computed_by_pipeline_version)
            VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000070',
                    'gaze_aversion_ratio', 'visual', 0.146, 'ratio', 'feature-eng@1.4.0')
            ON CONFLICT DO NOTHING;
        """))
        
        # NTS Scores
        await conn.execute(text("""
            INSERT INTO nts_scores (id, organization_id, meeting_id, participant_track_id, model_version_id,
                                     processing_job_id, nts_score, component_scores)
            VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000030',
                    '00000000-0000-0000-0000-000000000070', '00000000-0000-0000-0000-000000000051',
                    '00000000-0000-0000-0000-000000000060', 74.2,
                    '{"consistency":72.1,"engagement":65.4,"composure":80.0}'::jsonb)
            ON CONFLICT DO NOTHING;
        """))

    print("Reference data seeded successfully.")

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_data())
