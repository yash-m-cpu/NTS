"""row_level_security

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-06 22:39:00.000000

"""

from alembic import op

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
