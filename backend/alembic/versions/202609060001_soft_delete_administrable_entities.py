"""Add audit-safe soft deletion to administrable entities.

Revision ID: 202609060001
Revises: 202608090001
"""

from alembic import op
import sqlalchemy as sa


revision = "202609060001"
down_revision = "202608090001"
branch_labels = None
depends_on = None


TABLES = (
    "companies",
    "users",
    "storage_units",
    "devices",
    "iot_gateways",
    "sentinel_devices",
    "alert_contacts",
)


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index(f"ix_{table}_deleted_at", table, ["deleted_at"])


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_index(f"ix_{table}_deleted_at", table_name=table)
        op.drop_column(table, "deleted_at")
