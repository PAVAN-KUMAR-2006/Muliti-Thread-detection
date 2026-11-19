"""phone threat module: extend phone_reports (description, evidence, region, constraints, index) and add phone_scans.
Idempotent and data-preserving: every step checks what already exists, and no existing row is changed or deleted."""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
CATEGORIES = ("Spam Call", "Financial Scam", "Banking Fraud", "OTP Scam", "Impersonation", "Robocall", "Telemarketing", "Other")
UQ, CK, IX = "uq_phone_report_user_number_category", "ck_phone_report_category", "ix_phone_reports_number_created"


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("phone_reports")}
    uniques = {u["name"] for u in insp.get_unique_constraints("phone_reports")}
    checks = {c["name"] for c in insp.get_check_constraints("phone_reports")}
    indexes = {i["name"] for i in insp.get_indexes("phone_reports")}
    quoted = ", ".join(f"'{c}'" for c in CATEGORIES)
    bad_rows = bind.execute(sa.text(f"SELECT count(*) FROM phone_reports WHERE category NOT IN ({quoted})")).scalar() or 0
    with op.batch_alter_table("phone_reports") as b:
        if "description" not in cols:
            b.add_column(sa.Column("description", sa.Text(), nullable=False, server_default=""))
        if "evidence" not in cols:
            b.add_column(sa.Column("evidence", sa.String(500), nullable=True))
        if "region" not in cols:
            b.add_column(sa.Column("region", sa.String(2), nullable=True))
        if UQ not in uniques:
            b.create_unique_constraint(UQ, ["reported_by", "number", "category"])
        if CK not in checks and bad_rows == 0:  # never fail on, or alter, rows that already exist
            b.create_check_constraint(CK, f"category IN ({quoted})")
    if IX not in indexes:
        op.create_index(IX, "phone_reports", ["number", "created_at"])
    if "phone_scans" not in insp.get_table_names():
        op.create_table(
            "phone_scans",
            sa.Column("scan_id", sa.Uuid(), sa.ForeignKey("scans.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("number_e164", sa.String(20), nullable=False),
            sa.Column("region", sa.String(2), nullable=True),
            sa.Column("country_code", sa.Integer(), nullable=False),
            sa.Column("number_type", sa.String(32), nullable=False),
            sa.Column("display", sa.String(40), nullable=False),
        )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    tables = set(insp.get_table_names())
    if "phone_scans" in tables:
        op.drop_table("phone_scans")

    indexes = {i["name"] for i in insp.get_indexes("phone_reports")}
    if IX in indexes:
        op.drop_index(IX, table_name="phone_reports")

    uniques = {u["name"] for u in insp.get_unique_constraints("phone_reports")}
    checks = {c["name"] for c in insp.get_check_constraints("phone_reports")}
    columns = {c["name"] for c in insp.get_columns("phone_reports")}

    with op.batch_alter_table("phone_reports") as b:
        if UQ in uniques:
            b.drop_constraint(UQ, type_="unique")
        if CK in checks:
            b.drop_constraint(CK, type_="check")
        for column in ("region", "evidence", "description"):
            if column in columns:
                b.drop_column(column)