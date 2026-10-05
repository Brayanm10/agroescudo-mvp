"""Add explicit commissioning status to storage units.

Revision ID: 202610050001
Revises: 202609250001
"""

from alembic import op
import sqlalchemy as sa

revision = "202610050001"
down_revision = "202609250001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "storage_units",
        sa.Column("pilot_status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
    )
    op.create_index("ix_storage_units_pilot_status", "storage_units", ["pilot_status"])


def downgrade() -> None:
    op.drop_index("ix_storage_units_pilot_status", table_name="storage_units")
    op.drop_column("storage_units", "pilot_status")
