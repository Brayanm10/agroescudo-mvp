"""notifications and ai support

Revision ID: 202606070001
Revises: 202605310001
Create Date: 2026-06-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202606070001"
down_revision: Union[str, None] = "202605310001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("minimum_severity", sa.String(length=20), nullable=False, server_default="critical"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_preferences_channel"), "notification_preferences", ["channel"], unique=False)
    op.create_index(op.f("ix_notification_preferences_company_id"), "notification_preferences", ["company_id"], unique=False)
    op.create_index(op.f("ix_notification_preferences_enabled"), "notification_preferences", ["enabled"], unique=False)
    op.create_index(op.f("ix_notification_preferences_user_id"), "notification_preferences", ["user_id"], unique=False)

    op.create_table(
        "push_device_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False, server_default="android"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_push_device_tokens_company_id"), "push_device_tokens", ["company_id"], unique=False)
    op.create_index(op.f("ix_push_device_tokens_is_active"), "push_device_tokens", ["is_active"], unique=False)
    op.create_index(op.f("ix_push_device_tokens_token"), "push_device_tokens", ["token"], unique=True)
    op.create_index(op.f("ix_push_device_tokens_user_id"), "push_device_tokens", ["user_id"], unique=False)

    op.create_table(
        "notification_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_events_alert_id"), "notification_events", ["alert_id"], unique=False)
    op.create_index(op.f("ix_notification_events_channel"), "notification_events", ["channel"], unique=False)
    op.create_index(op.f("ix_notification_events_company_id"), "notification_events", ["company_id"], unique=False)
    op.create_index(op.f("ix_notification_events_status"), "notification_events", ["status"], unique=False)
    op.create_index(op.f("ix_notification_events_user_id"), "notification_events", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_events_user_id"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_status"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_company_id"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_channel"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_alert_id"), table_name="notification_events")
    op.drop_table("notification_events")

    op.drop_index(op.f("ix_push_device_tokens_user_id"), table_name="push_device_tokens")
    op.drop_index(op.f("ix_push_device_tokens_token"), table_name="push_device_tokens")
    op.drop_index(op.f("ix_push_device_tokens_is_active"), table_name="push_device_tokens")
    op.drop_index(op.f("ix_push_device_tokens_company_id"), table_name="push_device_tokens")
    op.drop_table("push_device_tokens")

    op.drop_index(op.f("ix_notification_preferences_user_id"), table_name="notification_preferences")
    op.drop_index(op.f("ix_notification_preferences_enabled"), table_name="notification_preferences")
    op.drop_index(op.f("ix_notification_preferences_company_id"), table_name="notification_preferences")
    op.drop_index(op.f("ix_notification_preferences_channel"), table_name="notification_preferences")
    op.drop_table("notification_preferences")
