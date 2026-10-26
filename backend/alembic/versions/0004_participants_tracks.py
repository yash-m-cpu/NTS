"""participants_tracks

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-06 22:33:00.000000

"""

from alembic import op

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
