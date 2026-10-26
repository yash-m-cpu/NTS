"""media_jobs

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-06 22:32:00.000000

"""

from alembic import op

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
