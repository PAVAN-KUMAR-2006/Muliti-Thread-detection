"""add confidence, status, explanation, recommendation to scans (keeps all existing data)"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    # A fresh database already gets these columns from 0001 (it builds from current models), so check first.
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("scans")}
    if "confidence" not in existing:
        op.add_column("scans", sa.Column("confidence", sa.Float(), nullable=True))
    if "status" not in existing:
        op.add_column("scans", sa.Column("status", sa.String(16), nullable=False, server_default="completed"))
    if "explanation" not in existing:
        op.add_column("scans", sa.Column("explanation", sa.Text(), nullable=False, server_default=""))
    if "recommendation" not in existing:
        op.add_column("scans", sa.Column("recommendation", sa.Text(), nullable=False, server_default=""))


def downgrade():
    for col in ("recommendation", "explanation", "status", "confidence"):
        op.drop_column("scans", col)
