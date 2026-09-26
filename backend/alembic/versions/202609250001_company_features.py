"""Add per-company feature entitlements.

Revision ID: 202609250001
Revises: 202609240001
"""

from alembic import op
import sqlalchemy as sa


revision = "202609250001"
down_revision = "202609240001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("feature_code", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("company_id", "feature_code", name="uq_company_features_company_code"),
    )
    op.create_index("ix_company_features_company_id", "company_features", ["company_id"])
    op.create_index("ix_company_features_feature_code", "company_features", ["feature_code"])
    op.create_index("ix_company_features_enabled", "company_features", ["enabled"])
    op.create_index("ix_company_features_enabled_by_id", "company_features", ["enabled_by_id"])


def downgrade() -> None:
    op.drop_index("ix_company_features_enabled_by_id", table_name="company_features")
    op.drop_index("ix_company_features_enabled", table_name="company_features")
    op.drop_index("ix_company_features_feature_code", table_name="company_features")
    op.drop_index("ix_company_features_company_id", table_name="company_features")
    op.drop_table("company_features")
