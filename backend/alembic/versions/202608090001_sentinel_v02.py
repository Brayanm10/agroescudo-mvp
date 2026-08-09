"""Add AgroEscudo Sentinel contacts, devices and job queue.

Revision ID: 202608090001
Revises: 202607240002
"""

from alembic import op
import sqlalchemy as sa


revision = "202608090001"
down_revision = "202607240002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("escalation_delay_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("receive_sms", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("receive_call", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("minimum_severity", sa.String(length=20), nullable=False, server_default="critical"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["storage_unit_id"], ["storage_units.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
    )
    op.create_index("ix_alert_contacts_company_id", "alert_contacts", ["company_id"])
    op.create_index("ix_alert_contacts_storage_unit_id", "alert_contacts", ["storage_unit_id"])
    op.create_index("ix_alert_contacts_phone_e164", "alert_contacts", ["phone_e164"])
    op.create_index("ix_alert_contacts_minimum_severity", "alert_contacts", ["minimum_severity"])
    op.create_index("ix_alert_contacts_active", "alert_contacts", ["active"])
    op.create_index("ix_alert_contacts_created_by_user_id", "alert_contacts", ["created_by_user_id"])
    op.create_index("ix_alert_contacts_scope", "alert_contacts", ["company_id", "storage_unit_id", "active"])

    op.create_table(
        "sentinel_devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_uid", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("firmware_version", sa.String(length=40), nullable=True),
        sa.Column("wifi_rssi", sa.Integer(), nullable=True),
        sa.Column("gsm_registered", sa.Boolean(), nullable=True),
        sa.Column("sim_ready", sa.Boolean(), nullable=True),
        sa.Column("last_ip", sa.String(length=80), nullable=True),
        sa.Column("token_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_uid"),
    )
    op.create_index("ix_sentinel_devices_active", "sentinel_devices", ["active"])
    op.create_index("ix_sentinel_devices_last_seen_at", "sentinel_devices", ["last_seen_at"])

    op.create_table(
        "sentinel_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("sentinel_device_id", sa.Integer(), nullable=True),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("alert_contact_id", sa.Integer(), nullable=False),
        sa.Column("notification_delivery_id", sa.Integer(), nullable=True),
        sa.Column("job_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("destination_phone", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("ring_seconds", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("not_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error_message", sa.String(length=500), nullable=True),
        sa.Column("result_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["sentinel_device_id"], ["sentinel_devices.id"]),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.ForeignKeyConstraint(["alert_contact_id"], ["alert_contacts.id"]),
        sa.ForeignKeyConstraint(["notification_delivery_id"], ["notification_deliveries.id"]),
        sa.UniqueConstraint("idempotency_key", name="uq_sentinel_jobs_idempotency_key"),
    )
    op.create_index("ix_sentinel_jobs_sentinel_device_id", "sentinel_jobs", ["sentinel_device_id"])
    op.create_index("ix_sentinel_jobs_alert_id", "sentinel_jobs", ["alert_id"])
    op.create_index("ix_sentinel_jobs_alert_contact_id", "sentinel_jobs", ["alert_contact_id"])
    op.create_index("ix_sentinel_jobs_notification_delivery_id", "sentinel_jobs", ["notification_delivery_id"])
    op.create_index("ix_sentinel_jobs_job_type", "sentinel_jobs", ["job_type"])
    op.create_index("ix_sentinel_jobs_status", "sentinel_jobs", ["status"])
    op.create_index("ix_sentinel_jobs_not_before", "sentinel_jobs", ["not_before"])
    op.create_index("ix_sentinel_jobs_expires_at", "sentinel_jobs", ["expires_at"])
    op.create_index("ix_sentinel_jobs_lease_until", "sentinel_jobs", ["lease_until"])
    op.create_index("ix_sentinel_jobs_claim", "sentinel_jobs", ["status", "not_before", "lease_until"])


def downgrade() -> None:
    op.drop_table("sentinel_jobs")
    op.drop_table("sentinel_devices")
    op.drop_table("alert_contacts")
