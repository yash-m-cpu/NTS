"""reports_llm

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-06 22:36:00.000000

"""

from alembic import op

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
