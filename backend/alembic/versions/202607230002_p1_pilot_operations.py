"""P1 pilot operations, maintenance, evidence, QR and firmware

Revision ID: 202607230002
Revises: 202607230001
Create Date: 2026-07-23 13:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607230002"
down_revision: Union[str, None] = "202607230001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("devices") as batch:
        batch.add_column(
            sa.Column("operational_status", sa.String(length=32), nullable=False, server_default="operational")
        )
        batch.add_column(sa.Column("expected_reading_interval_minutes", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("public_token", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("qr_version", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("qr_created_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("qr_revoked_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("qr_last_scanned_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_devices_operational_status", ["operational_status"])
        batch.create_index("ix_devices_public_token", ["public_token"], unique=True)

    with op.batch_alter_table("iot_gateways") as batch:
        batch.add_column(sa.Column("company_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("site_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("storage_unit_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=32), nullable=False, server_default="UNKNOWN"))
        batch.add_column(
            sa.Column("internet_status", sa.String(length=32), nullable=False, server_default="unknown")
        )
        batch.add_column(sa.Column("local_queue_size", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("associated_devices_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("restart_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("last_restart_reason", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("last_error_code", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("ip_address_sanitized", sa.String(length=80), nullable=True))
        batch.create_foreign_key("fk_iot_gateways_company_id", "companies", ["company_id"], ["id"])
        batch.create_foreign_key("fk_iot_gateways_site_id", "sites", ["site_id"], ["id"])
        batch.create_foreign_key(
            "fk_iot_gateways_storage_unit_id",
            "storage_units",
            ["storage_unit_id"],
            ["id"],
        )
        batch.create_index("ix_iot_gateways_company_id", ["company_id"])
        batch.create_index("ix_iot_gateways_site_id", ["site_id"])
        batch.create_index("ix_iot_gateways_storage_unit_id", ["storage_unit_id"])
        batch.create_index("ix_iot_gateways_status", ["status"])
        batch.create_index("ix_iot_gateways_internet_status", ["internet_status"])

    with op.batch_alter_table("iot_devices") as batch:
        batch.add_column(sa.Column("gateway_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_iot_devices_gateway_id", "iot_gateways", ["gateway_id"], ["id"])
        batch.create_index("ix_iot_devices_gateway_id", ["gateway_id"])

    op.create_table(
        "maintenance_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("service_case_id", sa.Integer(), sa.ForeignKey("service_cases.id"), nullable=True),
        sa.Column("parent_maintenance_id", sa.Integer(), nullable=True),
        sa.Column("maintenance_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="SCHEDULED"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("device_status_after", sa.String(length=40), nullable=True),
        sa.Column("parts_replaced_json", sa.Text(), nullable=True),
        sa.Column("battery_replaced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensor_replaced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("calibration_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("firmware_updated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("previous_firmware_version", sa.String(length=80), nullable=True),
        sa.Column("new_firmware_version", sa.String(length=80), nullable=True),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_maintenance_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["parent_maintenance_id"],
            ["maintenance_records.id"],
            name="fk_maintenance_records_parent",
        ),
    )
    for column in (
        "company_id",
        "storage_unit_id",
        "device_id",
        "service_case_id",
        "parent_maintenance_id",
        "status",
        "priority",
        "scheduled_at",
        "technician_id",
        "created_by_id",
        "next_maintenance_at",
        "created_at",
    ):
        op.create_index(f"ix_maintenance_records_{column}", "maintenance_records", [column])
    op.create_index(
        "ix_maintenance_records_scope_status",
        "maintenance_records",
        ["company_id", "storage_unit_id", "status"],
    )
    op.create_index(
        "ix_maintenance_records_device_schedule",
        "maintenance_records",
        ["device_id", "scheduled_at"],
    )

    op.create_table(
        "maintenance_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "maintenance_id",
            sa.Integer(),
            sa.ForeignKey("maintenance_records.id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    for column in ("maintenance_id", "user_id", "event_type", "created_at"):
        op.create_index(f"ix_maintenance_events_{column}", "maintenance_events", [column])

    op.create_table(
        "installation_checklists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="DRAFT"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checklist_version", sa.String(length=32), nullable=False, server_default="p1-v1"),
        sa.Column("responses_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("first_reading_id", sa.Integer(), sa.ForeignKey("sensor_readings.id"), nullable=True),
        sa.Column("test_alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("validation_errors_json", sa.Text(), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    for column in (
        "company_id",
        "storage_unit_id",
        "device_id",
        "technician_id",
        "status",
        "first_reading_id",
        "test_alert_id",
        "created_by_id",
        "created_at",
    ):
        op.create_index(f"ix_installation_checklists_{column}", "installation_checklists", [column])
    op.create_index(
        "ix_installation_checklists_scope_status",
        "installation_checklists",
        ["company_id", "storage_unit_id", "status"],
    )

    with op.batch_alter_table("stored_files") as batch:
        batch.add_column(sa.Column("storage_unit_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("entity_type", sa.String(length=40), nullable=True))
        batch.add_column(sa.Column("entity_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("file_type", sa.String(length=32), nullable=False, server_default="OTHER"))
        batch.add_column(sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("description", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key(
            "fk_stored_files_storage_unit_id",
            "storage_units",
            ["storage_unit_id"],
            ["id"],
        )
        batch.create_index("ix_stored_files_storage_unit_id", ["storage_unit_id"])
        batch.create_index("ix_stored_files_entity_type", ["entity_type"])
        batch.create_index("ix_stored_files_entity_id", ["entity_id"])
        batch.create_index("ix_stored_files_file_type", ["file_type"])
        batch.create_index("ix_stored_files_is_sensitive", ["is_sensitive"])
        batch.create_index("ix_stored_files_deleted_at", ["deleted_at"])

    op.create_table(
        "firmware_releases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_type", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("release_notes", sa.Text(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "device_type",
            "version",
            name="uq_firmware_releases_device_type_version",
        ),
    )
    for column in ("device_type", "version", "status", "created_by_id", "is_recommended", "is_mandatory"):
        op.create_index(f"ix_firmware_releases_{column}", "firmware_releases", [column])

    op.create_table(
        "firmware_update_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column(
            "firmware_release_id",
            sa.Integer(),
            sa.ForeignKey("firmware_releases.id"),
            nullable=True,
        ),
        sa.Column(
            "maintenance_id",
            sa.Integer(),
            sa.ForeignKey("maintenance_records.id"),
            nullable=True,
        ),
        sa.Column("previous_version", sa.String(length=80), nullable=True),
        sa.Column("new_version", sa.String(length=80), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    for column in (
        "company_id",
        "storage_unit_id",
        "device_id",
        "firmware_release_id",
        "maintenance_id",
        "result",
        "recorded_by_id",
        "recorded_at",
    ):
        op.create_index(f"ix_firmware_update_records_{column}", "firmware_update_records", [column])

    with op.batch_alter_table("notification_deliveries") as batch:
        batch.add_column(sa.Column("company_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("incident_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("maintenance_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("provider", sa.String(length=40), nullable=True))
        batch.add_column(sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("error_code", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("error_message_sanitized", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("provider_message_id", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("idempotency_key", sa.String(length=160), nullable=True))
        batch.add_column(sa.Column("payload_version", sa.String(length=32), nullable=False, server_default="v1"))
        batch.create_foreign_key(
            "fk_notification_deliveries_company_id",
            "companies",
            ["company_id"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_notification_deliveries_incident_id",
            "service_cases",
            ["incident_id"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_notification_deliveries_maintenance_id",
            "maintenance_records",
            ["maintenance_id"],
            ["id"],
        )
        batch.create_index("ix_notification_deliveries_company_id", ["company_id"])
        batch.create_index("ix_notification_deliveries_incident_id", ["incident_id"])
        batch.create_index("ix_notification_deliveries_maintenance_id", ["maintenance_id"])
        batch.create_index("ix_notification_deliveries_next_retry_at", ["next_retry_at"])
        batch.create_index(
            "ix_notification_deliveries_idempotency_key",
            ["idempotency_key"],
            unique=True,
        )

    op.execute(
        sa.text(
            "UPDATE notification_deliveries SET company_id = "
            "(SELECT company_id FROM users WHERE users.id = notification_deliveries.user_id) "
            "WHERE company_id IS NULL AND user_id IS NOT NULL"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("notification_deliveries") as batch:
        batch.drop_index("ix_notification_deliveries_idempotency_key")
        batch.drop_index("ix_notification_deliveries_next_retry_at")
        batch.drop_index("ix_notification_deliveries_maintenance_id")
        batch.drop_index("ix_notification_deliveries_incident_id")
        batch.drop_index("ix_notification_deliveries_company_id")
        batch.drop_constraint("fk_notification_deliveries_maintenance_id", type_="foreignkey")
        batch.drop_constraint("fk_notification_deliveries_incident_id", type_="foreignkey")
        batch.drop_constraint("fk_notification_deliveries_company_id", type_="foreignkey")
        for column in (
            "payload_version",
            "idempotency_key",
            "next_retry_at",
            "retry_count",
            "provider_message_id",
            "error_message_sanitized",
            "error_code",
            "failed_at",
            "delivered_at",
            "sent_at",
            "attempted_at",
            "provider",
            "maintenance_id",
            "incident_id",
            "company_id",
        ):
            batch.drop_column(column)

    op.drop_table("firmware_update_records")
    op.drop_table("firmware_releases")

    with op.batch_alter_table("stored_files") as batch:
        batch.drop_index("ix_stored_files_deleted_at")
        batch.drop_index("ix_stored_files_is_sensitive")
        batch.drop_index("ix_stored_files_file_type")
        batch.drop_index("ix_stored_files_entity_id")
        batch.drop_index("ix_stored_files_entity_type")
        batch.drop_index("ix_stored_files_storage_unit_id")
        batch.drop_constraint("fk_stored_files_storage_unit_id", type_="foreignkey")
        for column in (
            "deleted_at",
            "is_sensitive",
            "description",
            "captured_at",
            "file_type",
            "entity_id",
            "entity_type",
            "storage_unit_id",
        ):
            batch.drop_column(column)

    op.drop_table("installation_checklists")
    op.drop_table("maintenance_events")
    op.drop_table("maintenance_records")

    with op.batch_alter_table("iot_devices") as batch:
        batch.drop_index("ix_iot_devices_gateway_id")
        batch.drop_constraint("fk_iot_devices_gateway_id", type_="foreignkey")
        batch.drop_column("gateway_id")

    with op.batch_alter_table("iot_gateways") as batch:
        batch.drop_index("ix_iot_gateways_internet_status")
        batch.drop_index("ix_iot_gateways_status")
        batch.drop_index("ix_iot_gateways_storage_unit_id")
        batch.drop_index("ix_iot_gateways_site_id")
        batch.drop_index("ix_iot_gateways_company_id")
        batch.drop_constraint("fk_iot_gateways_storage_unit_id", type_="foreignkey")
        batch.drop_constraint("fk_iot_gateways_site_id", type_="foreignkey")
        batch.drop_constraint("fk_iot_gateways_company_id", type_="foreignkey")
        for column in (
            "ip_address_sanitized",
            "last_error_at",
            "last_error_code",
            "last_restart_reason",
            "restart_count",
            "associated_devices_count",
            "local_queue_size",
            "internet_status",
            "status",
            "storage_unit_id",
            "site_id",
            "company_id",
        ):
            batch.drop_column(column)

    with op.batch_alter_table("devices") as batch:
        batch.drop_index("ix_devices_public_token")
        batch.drop_index("ix_devices_operational_status")
        for column in (
            "qr_last_scanned_at",
            "qr_revoked_at",
            "qr_created_at",
            "qr_version",
            "public_token",
            "expected_reading_interval_minutes",
            "operational_status",
        ):
            batch.drop_column(column)
