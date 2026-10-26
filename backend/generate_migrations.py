import os

versions_dir = 'c:/PJT/backend/alembic/versions'
os.makedirs(versions_dir, exist_ok=True)

migrations = {
    '0001_core_identity.py': '''"""core_identity

Revision ID: 0001
Revises: 
Create Date: 2026-09-06 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email CITEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'invited'
    CHECK (status IN ('active','invited','suspended','deleted')),
  email_verified_at TIMESTAMPTZ,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_users_status ON users(status);
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug CITEXT NOT NULL UNIQUE,
  plan_tier TEXT NOT NULL DEFAULT 'free' CHECK (plan_tier IN ('free','pro','enterprise')),
  settings JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE TRIGGER trg_organizations_updated_at BEFORE UPDATE ON organizations
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE organization_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('ADMIN','MANAGER','ANALYST','RESEARCHER','USER')),
  invited_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (organization_id, user_id)
);
CREATE INDEX idx_org_members_user ON organization_members(user_id);
CREATE INDEX idx_org_members_org_role ON organization_members(organization_id, role);
CREATE TRIGGER trg_org_members_updated_at BEFORE UPDATE ON organization_members
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

def downgrade():
    pass
''',
    '0002_projects_meetings.py': '''"""projects_meetings

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-06 22:31:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (organization_id, name)
);
CREATE INDEX idx_projects_org ON projects(organization_id);
CREATE INDEX idx_projects_org_status ON projects(organization_id, status);
CREATE TRIGGER trg_projects_updated_at BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE meetings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('upload','live_camera','zoom_bot','teams_bot')),
  scheduled_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  duration_seconds INTEGER,
  status TEXT NOT NULL DEFAULT 'scheduled'
    CHECK (status IN ('scheduled','recording','uploaded','processing','analyzed','failed')),
  created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_meetings_org_project ON meetings(organization_id, project_id);
CREATE INDEX idx_meetings_status ON meetings(status);
CREATE INDEX idx_meetings_started_at ON meetings(started_at);
CREATE TRIGGER trg_meetings_updated_at BEFORE UPDATE ON meetings
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE meeting_participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL,
  email CITEXT,
  role_in_meeting TEXT,
  external_platform_id TEXT,
  joined_at TIMESTAMPTZ,
  left_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_meeting_participants_meeting ON meeting_participants(meeting_id);
CREATE UNIQUE INDEX uq_meeting_participants_platform
  ON meeting_participants(meeting_id, external_platform_id)
  WHERE external_platform_id IS NOT NULL;
CREATE TRIGGER trg_meeting_participants_updated_at BEFORE UPDATE ON meeting_participants
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

def downgrade():
    pass
''',
    '0003_media_jobs.py': '''"""media_jobs

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-06 22:32:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
CREATE TABLE media_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  asset_type TEXT NOT NULL CHECK (asset_type IN ('video','audio','screen_share','combined')),
  storage_bucket TEXT NOT NULL,
  storage_key TEXT NOT NULL,
  storage_provider TEXT NOT NULL CHECK (storage_provider IN ('s3','gcs','azure_blob','minio')),
  content_type TEXT NOT NULL,
  size_bytes BIGINT,
  duration_seconds NUMERIC(10,3),
  checksum_sha256 TEXT,
  resolution TEXT,
  codec TEXT,
  upload_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (upload_status IN ('pending','uploaded','verified','quarantined','failed')),
  uploaded_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ,
  UNIQUE (storage_bucket, storage_key)
);
CREATE INDEX idx_media_assets_meeting ON media_assets(meeting_id);
CREATE INDEX idx_media_assets_org ON media_assets(organization_id);
CREATE INDEX idx_media_assets_upload_status ON media_assets(upload_status);
CREATE TRIGGER trg_media_assets_updated_at BEFORE UPDATE ON media_assets
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE model_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_family TEXT NOT NULL CHECK (model_family IN ('cv_extraction','nts_scoring','llm_narrative','archetype_classifier')),
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  artifact_uri TEXT,
  training_dataset_id UUID,
  hyperparameters JSONB,
  metrics JSONB,
  status TEXT NOT NULL DEFAULT 'staging' CHECK (status IN ('staging','active','deprecated','retired')),
  released_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (model_family, name, version)
);
CREATE INDEX idx_model_versions_family_status ON model_versions(model_family, status);
CREATE TRIGGER trg_model_versions_updated_at BEFORE UPDATE ON model_versions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE processing_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  media_asset_id UUID REFERENCES media_assets(id) ON DELETE SET NULL,
  job_type TEXT NOT NULL CHECK (job_type IN ('cv_extraction','stt_transcription','feature_fusion','nts_scoring','report_generation')),
  model_version_id UUID REFERENCES model_versions(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
  priority SMALLINT NOT NULL DEFAULT 0,
  queue_name TEXT NOT NULL DEFAULT 'default',
  attempt_count SMALLINT NOT NULL DEFAULT 0,
  max_attempts SMALLINT NOT NULL DEFAULT 3,
  progress_pct SMALLINT CHECK (progress_pct BETWEEN 0 AND 100),
  error_message TEXT,
  error_detail JSONB,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_jobs_meeting ON processing_jobs(meeting_id);
CREATE INDEX idx_jobs_status_queue ON processing_jobs(status, queue_name);
CREATE INDEX idx_jobs_org_status ON processing_jobs(organization_id, status);
CREATE TRIGGER trg_processing_jobs_updated_at BEFORE UPDATE ON processing_jobs
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE processing_job_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  processing_job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN ('queued','started','progress','succeeded','failed','retrying','cancelled')),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_job_events_job_time ON processing_job_events(processing_job_id, occurred_at);
    """)

def downgrade():
    pass
''',
    '0004_participants_tracks.py': '''"""participants_tracks

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-06 22:33:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
CREATE TABLE participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL,
  external_reference TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_participants_org ON participants(organization_id);
CREATE TRIGGER trg_participants_updated_at BEFORE UPDATE ON participants
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE participant_tracks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  media_asset_id UUID NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  meeting_participant_id UUID REFERENCES meeting_participants(id) ON DELETE SET NULL,
  participant_id UUID REFERENCES participants(id) ON DELETE SET NULL,
  processing_job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE RESTRICT,
  track_label TEXT NOT NULL,
  first_seen_at_ms INTEGER NOT NULL,
  last_seen_at_ms INTEGER NOT NULL,
  detection_frame_count INTEGER,
  avg_detection_confidence NUMERIC(5,4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_tracks_media ON participant_tracks(media_asset_id);
CREATE INDEX idx_tracks_job ON participant_tracks(processing_job_id);
CREATE INDEX idx_tracks_meeting_participant ON participant_tracks(meeting_participant_id);
CREATE TRIGGER trg_participant_tracks_updated_at BEFORE UPDATE ON participant_tracks
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

def downgrade():
    pass
''',
    '0005_features_metrics.py': '''"""features_metrics

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-06 22:34:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
CREATE TABLE feature_extractions (
  id UUID NOT NULL DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  participant_track_id UUID NOT NULL REFERENCES participant_tracks(id) ON DELETE CASCADE,
  media_asset_id UUID NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
  processing_job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE RESTRICT,
  model_version_id UUID NOT NULL REFERENCES model_versions(id) ON DELETE RESTRICT,
  extraction_pipeline_version TEXT NOT NULL,
  feature_type TEXT NOT NULL CHECK (feature_type IN
    ('face_pose','body_pose','hand_pose','gaze','emotion','gesture','voice_prosody','speaker_turn')),
  timestamp_ms INTEGER NOT NULL,
  frame_index INTEGER,
  confidence NUMERIC(5,4),
  values JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE feature_extractions_default PARTITION OF feature_extractions DEFAULT;

CREATE INDEX idx_features_track_time ON feature_extractions(participant_track_id, timestamp_ms);
CREATE INDEX idx_features_job ON feature_extractions(processing_job_id);
CREATE INDEX idx_features_type_time ON feature_extractions(feature_type, timestamp_ms);
CREATE INDEX idx_features_values_gin ON feature_extractions USING GIN (values);

CREATE TABLE feature_windows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  participant_track_id UUID NOT NULL REFERENCES participant_tracks(id) ON DELETE CASCADE,
  feature_type TEXT NOT NULL,
  window_start_ms INTEGER NOT NULL,
  window_end_ms INTEGER NOT NULL,
  aggregation JSONB NOT NULL,
  source_extraction_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (participant_track_id, feature_type, window_start_ms, window_end_ms)
);
CREATE INDEX idx_windows_track_time ON feature_windows(participant_track_id, window_start_ms);

CREATE TABLE behavioral_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  participant_track_id UUID NOT NULL REFERENCES participant_tracks(id) ON DELETE CASCADE,
  metric_key TEXT NOT NULL,
  metric_category TEXT NOT NULL CHECK (metric_category IN ('visual','vocal','linguistic','temporal')),
  window_start_ms INTEGER,
  window_end_ms INTEGER,
  value NUMERIC(12,6) NOT NULL,
  unit TEXT,
  computed_by_pipeline_version TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_metrics_track_key ON behavioral_metrics(participant_track_id, metric_key);
CREATE INDEX idx_metrics_key_window ON behavioral_metrics(metric_key, window_start_ms);
    """)

def downgrade():
    pass
''',
    '0006_scores_archetypes.py': '''"""scores_archetypes

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-06 22:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
CREATE TABLE nts_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  participant_track_id UUID REFERENCES participant_tracks(id) ON DELETE CASCADE,
  model_version_id UUID NOT NULL REFERENCES model_versions(id) ON DELETE RESTRICT,
  processing_job_id UUID NOT NULL REFERENCES processing_jobs(id) ON DELETE RESTRICT,
  nts_score NUMERIC(6,3) NOT NULL,
  confidence_interval_low NUMERIC(6,3),
  confidence_interval_high NUMERIC(6,3),
  component_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
  input_metric_ids UUID[],
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_nts_meeting ON nts_scores(meeting_id);
CREATE INDEX idx_nts_track ON nts_scores(participant_track_id);
CREATE INDEX idx_nts_model_version ON nts_scores(model_version_id);

CREATE TABLE model_predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  model_version_id UUID NOT NULL REFERENCES model_versions(id) ON DELETE RESTRICT,
  nts_score_id UUID REFERENCES nts_scores(id) ON DELETE CASCADE,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('participant_track','meeting')),
  subject_id UUID NOT NULL,
  prediction_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_predictions_subject ON model_predictions(subject_type, subject_id);
CREATE INDEX idx_predictions_model_version ON model_predictions(model_version_id);

CREATE TABLE archetypes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_archetypes_updated_at BEFORE UPDATE ON archetypes
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE participant_archetypes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  participant_track_id UUID NOT NULL REFERENCES participant_tracks(id) ON DELETE CASCADE,
  archetype_id UUID NOT NULL REFERENCES archetypes(id) ON DELETE RESTRICT,
  model_version_id UUID NOT NULL REFERENCES model_versions(id) ON DELETE RESTRICT,
  confidence NUMERIC(5,4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (participant_track_id, model_version_id)
);
CREATE INDEX idx_participant_archetypes_track ON participant_archetypes(participant_track_id);
    """)

def downgrade():
    pass
''',
    '0007_reports_llm.py': '''"""reports_llm

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-06 22:36:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
CREATE TABLE reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  generated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  processing_job_id UUID REFERENCES processing_jobs(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','final','archived')),
  export_format TEXT CHECK (export_format IN ('pdf','html','json')),
  storage_bucket TEXT,
  storage_key TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX idx_reports_meeting ON reports(meeting_id);
CREATE INDEX idx_reports_org_status ON reports(organization_id, status);
CREATE TRIGGER trg_reports_updated_at BEFORE UPDATE ON reports
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE report_sections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  section_key TEXT NOT NULL,
  title TEXT NOT NULL,
  order_index SMALLINT NOT NULL,
  content_markdown TEXT,
  content_source TEXT NOT NULL CHECK (content_source IN ('llm_generated','template','manual_edit')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (report_id, section_key)
);
CREATE INDEX idx_report_sections_report_order ON report_sections(report_id, order_index);
CREATE TRIGGER trg_report_sections_updated_at BEFORE UPDATE ON report_sections
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE llm_generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  report_section_id UUID REFERENCES report_sections(id) ON DELETE SET NULL,
  nts_score_id UUID REFERENCES nts_scores(id) ON DELETE SET NULL,
  model_version_id UUID NOT NULL REFERENCES model_versions(id) ON DELETE RESTRICT,
  prompt_template_key TEXT NOT NULL,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  input_context JSONB,
  output_text TEXT NOT NULL,
  latency_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_llm_gen_report_section ON llm_generations(report_section_id);
CREATE INDEX idx_llm_gen_nts_score ON llm_generations(nts_score_id);
    """)

def downgrade():
    pass
''',
    '0008_datasets_audit.py': '''"""datasets_audit

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-06 22:37:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
CREATE TABLE datasets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK (purpose IN ('training','evaluation','calibration')),
  description TEXT,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_datasets_org ON datasets(organization_id);
CREATE TRIGGER trg_datasets_updated_at BEFORE UPDATE ON datasets
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE model_versions
  ADD CONSTRAINT fk_model_versions_dataset
  FOREIGN KEY (training_dataset_id) REFERENCES datasets(id) ON DELETE SET NULL;

CREATE TABLE dataset_samples (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,
  participant_track_id UUID REFERENCES participant_tracks(id) ON DELETE SET NULL,
  label JSONB,
  split TEXT CHECK (split IN ('train','val','test')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_dataset_samples_dataset ON dataset_samples(dataset_id);
CREATE INDEX idx_dataset_samples_track ON dataset_samples(participant_track_id);

CREATE TABLE experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
  resulting_model_version_id UUID REFERENCES model_versions(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  config JSONB,
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','completed','failed')),
  metrics JSONB,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_experiments_dataset ON experiments(dataset_id);
CREATE INDEX idx_experiments_status ON experiments(status);
CREATE TRIGGER trg_experiments_updated_at BEFORE UPDATE ON experiments
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id UUID,
  ip_address INET,
  user_agent TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_org_time ON audit_logs(organization_id, occurred_at);
CREATE INDEX idx_audit_actor ON audit_logs(actor_user_id);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
    """)

def downgrade():
    pass
''',
    '0009_refresh_tokens.py': '''"""refresh_tokens

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-06 22:38:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
CREATE TABLE refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
    """)

def downgrade():
    pass
''',
    '0010_row_level_security.py': '''"""row_level_security

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-06 22:39:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
-- RLS cannot be easily created without setting up the current_setting logic in actual postgres, 
-- but we can add the DDL for completeness as per schema docs.
-- Since this is an MVP without active Postgres instances testing RLS right now, we wrap it in basic policy statements.

-- In a real setup, we'd need to create roles. We'll just define the policies.

DO $$ 
DECLARE
    tname text;
BEGIN
    FOR tname IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE column_name = 'organization_id' 
          AND table_schema = 'public' 
          AND table_name NOT IN ('organizations', 'organization_members', 'audit_logs', 'datasets')
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', tname);
        EXECUTE format('CREATE POLICY tenant_isolation_%I ON %I USING (organization_id::text = current_setting(''app.current_org_id'', true));', tname, tname);
    END LOOP;
END $$;
    """)

def downgrade():
    pass
'''
}

for filename, content in migrations.items():
    path = os.path.join(versions_dir, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

print(f"Created {len(migrations)} migration files successfully.")
