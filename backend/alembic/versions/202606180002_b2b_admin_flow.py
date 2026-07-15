"""b2b admin flow fields

Revision ID: 202606180002
Revises: 202606180001
Create Date: 2026-06-18 03:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202606180002"
down_revision: Union[str, None] = "202606180001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch:
        batch.add_column(sa.Column("type", sa.String(length=40), nullable=False, server_default="acopiador"))
        batch.add_column(sa.Column("city", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("contact_name", sa.String(length=160), nullable=True))
        batch.add_column(sa.Column("contact_email", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("contact_phone", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_companies_type", ["type"])
        batch.create_index("ix_companies_is_active", ["is_active"])

    with op.batch_alter_table("users") as batch:
        batch.alter_column("company_id", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("phone_whatsapp", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("telegram_chat_id", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("receives_alerts", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("storage_units") as batch:
        batch.add_column(sa.Column("location", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("crop_type", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_storage_units_is_active", ["is_active"])

    with op.batch_alter_table("devices") as batch:
        batch.add_column(sa.Column("device_type", sa.String(length=80), nullable=False, server_default="esp32_iot_node"))
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_devices_device_type", ["device_type"])


def downgrade() -> None:
    with op.batch_alter_table("devices") as batch:
        batch.drop_index("ix_devices_device_type")
        batch.drop_column("updated_at")
        batch.drop_column("last_seen_at")
        batch.drop_column("device_type")

    with op.batch_alter_table("storage_units") as batch:
        batch.drop_index("ix_storage_units_is_active")
        batch.drop_column("updated_at")
        batch.drop_column("is_active")
        batch.drop_column("crop_type")
        batch.drop_column("location")

    with op.batch_alter_table("users") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("receives_alerts")
        batch.drop_column("telegram_chat_id")
        batch.drop_column("phone_whatsapp")
        batch.alter_column("company_id", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("companies") as batch:
        batch.drop_index("ix_companies_is_active")
        batch.drop_index("ix_companies_type")
        batch.drop_column("updated_at")
        batch.drop_column("is_active")
        batch.drop_column("contact_phone")
        batch.drop_column("contact_email")
        batch.drop_column("contact_name")
        batch.drop_column("city")
        batch.drop_column("type")
