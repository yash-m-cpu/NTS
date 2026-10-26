"""features_metrics

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-06 22:34:00.000000

"""

from alembic import op

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
