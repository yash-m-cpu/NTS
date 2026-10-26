"""datasets_audit

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-06 22:37:00.000000

"""

from alembic import op

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
