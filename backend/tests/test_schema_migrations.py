import os

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import settings


@pytest.mark.skip(reason="No live Postgres available in this environment")
def test_migrations():
    """Verify migrations apply correctly."""
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))
    
    # Run migrations
    command.upgrade(alembic_cfg, "head")
    
    # Downgrade 
    command.downgrade(alembic_cfg, "base")
