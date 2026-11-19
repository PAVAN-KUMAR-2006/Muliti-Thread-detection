"""initial schema: users, sessions, password_resets, scans and scan detail tables"""
from alembic import op
from app.database import Base
import app.models  # noqa: F401

revision = "0001"
down_revision = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
