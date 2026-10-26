"""scores_archetypes

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-06 22:35:00.000000

"""

from alembic import op

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
