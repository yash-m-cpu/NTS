"""refresh_tokens

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-06 22:38:00.000000

"""

from alembic import op

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
