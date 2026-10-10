"""Add optional per-unit EMC calibration.

Revision ID: 202610100001
Revises: 202610050001
"""

from alembic import op
import sqlalchemy as sa

revision = "202610100001"
down_revision = "202610050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("storage_units", sa.Column("emc_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("storage_units", sa.Column("emc_crop", sa.String(length=40), nullable=False, server_default="MAIZE"))
    op.add_column("storage_units", sa.Column("emc_reference_moisture_wb", sa.Float(), nullable=True))
    op.add_column("storage_units", sa.Column("emc_reference_timestamp", sa.DateTime(timezone=True), nullable=True))
    op.add_column("storage_units", sa.Column("emc_raw_at_reference_wb", sa.Float(), nullable=True))
    op.add_column("storage_units", sa.Column("emc_calibration_offset_pp", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("storage_units", "emc_calibration_offset_pp")
    op.drop_column("storage_units", "emc_raw_at_reference_wb")
    op.drop_column("storage_units", "emc_reference_timestamp")
    op.drop_column("storage_units", "emc_reference_moisture_wb")
    op.drop_column("storage_units", "emc_crop")
    op.drop_column("storage_units", "emc_enabled")
