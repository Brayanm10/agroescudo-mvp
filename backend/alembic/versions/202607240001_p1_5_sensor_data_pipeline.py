"""P1.5 canonical metrics, explicit channels and normalized telemetry

Revision ID: 202607240001
Revises: 202607230002
Create Date: 2026-07-24 01:30:00.000000

This migration is strictly additive. Legacy telemetry tables and values remain
untouched and queryable.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.domain.metric_registry import METRIC_REGISTRY


revision: str = "202607240001"
down_revision: Union[str, None] = "202607230002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metric_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numeric_id", sa.Integer(), nullable=False),
        sa.Column("metric_code", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("canonical_unit", sa.String(length=24), nullable=False),
        sa.Column("storage_type", sa.String(length=24), nullable=False),
        sa.Column("scale_factor", sa.Float(), nullable=False),
        sa.Column("physical_min", sa.Float(), nullable=True),
        sa.Column("physical_max", sa.Float(), nullable=True),
        sa.Column("default_decimals", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("default_chart_type", sa.String(length=32), nullable=False, server_default="line"),
        sa.Column("product_compatibility", sa.String(length=160), nullable=False),
        sa.Column("client_visibility", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_derived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("calibration_method", sa.String(length=40), nullable=True),
        sa.Column("alert_supported", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("registry_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("numeric_id", name="uq_metric_definitions_numeric_id"),
        sa.UniqueConstraint("metric_code", name="uq_metric_definitions_metric_code"),
    )
    op.create_index("ix_metric_definitions_numeric_id", "metric_definitions", ["numeric_id"], unique=True)
    op.create_index("ix_metric_definitions_metric_code", "metric_definitions", ["metric_code"], unique=True)

    definitions = sa.table(
        "metric_definitions",
        sa.column("numeric_id", sa.Integer()),
        sa.column("metric_code", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("canonical_unit", sa.String()),
        sa.column("storage_type", sa.String()),
        sa.column("scale_factor", sa.Float()),
        sa.column("physical_min", sa.Float()),
        sa.column("physical_max", sa.Float()),
        sa.column("default_decimals", sa.Integer()),
        sa.column("default_chart_type", sa.String()),
        sa.column("product_compatibility", sa.String()),
        sa.column("client_visibility", sa.Boolean()),
        sa.column("is_derived", sa.Boolean()),
        sa.column("calibration_method", sa.String()),
        sa.column("alert_supported", sa.Boolean()),
        sa.column("display_order", sa.Integer()),
        sa.column("registry_version", sa.Integer()),
    )
    op.bulk_insert(definitions, [metric.as_record() for metric in METRIC_REGISTRY])

    with op.batch_alter_table("devices") as batch:
        batch.add_column(sa.Column("template_code", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("capabilities_version", sa.Integer(), nullable=False, server_default="1"))
        batch.create_index("ix_devices_template_code", ["template_code"])

    with op.batch_alter_table("device_channels") as batch:
        batch.add_column(sa.Column("channel_key", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("sensor_type", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("hardware_port", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("metric_codes", sa.Text(), nullable=True))
        batch.add_column(sa.Column("canonical_unit", sa.String(length=24), nullable=True))
        batch.add_column(sa.Column("is_installed", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("is_visible_to_client", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("chart_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("alert_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("calibration_required", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(
            sa.Column("status", sa.String(length=40), nullable=False, server_default="CONFIGURED_NOT_SEEN")
        )
        batch.add_column(sa.Column("display_name", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("last_valid_reading_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("retired_by_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("retirement_reason", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        sa.text(
            "UPDATE device_channels SET "
            "channel_key = code, "
            "metric_codes = metric_type, "
            "canonical_unit = unit, "
            "display_name = name, "
            "updated_at = created_at "
            "WHERE channel_key IS NULL"
        )
    )
    with op.batch_alter_table("device_channels") as batch:
        batch.alter_column("channel_key", existing_type=sa.String(length=80), nullable=False)
        batch.alter_column("updated_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch.create_foreign_key("fk_device_channels_retired_by_id", "users", ["retired_by_id"], ["id"])
        batch.create_index("ix_device_channels_channel_key", ["channel_key"])
        batch.create_index("ix_device_channels_is_installed", ["is_installed"])
        batch.create_index("ix_device_channels_is_enabled", ["is_enabled"])
        batch.create_index("ix_device_channels_status", ["status"])
        batch.create_index("ix_device_channels_retired_by_id", ["retired_by_id"])
        batch.create_unique_constraint(
            "uq_device_channels_device_channel_key",
            ["device_id", "channel_key"],
        )

    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("gateway_id", sa.Integer(), sa.ForeignKey("iot_gateways.id"), nullable=True),
        sa.Column("sensor_reading_id", sa.Integer(), sa.ForeignKey("sensor_readings.id"), nullable=True),
        sa.Column("iot_reading_id", sa.Integer(), sa.ForeignKey("iot_readings.id"), nullable=True),
        sa.Column("boot_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("sample_counter", sa.Integer(), nullable=False),
        sa.Column("sampled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at_gateway", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at_cloud", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("time_quality", sa.String(length=32), nullable=False),
        sa.Column("firmware_version", sa.String(length=40), nullable=True),
        sa.Column("protocol_version", sa.Integer(), nullable=False),
        sa.Column("capabilities_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sensor_status_flags", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_payload_hash", sa.String(length=64), nullable=True),
        sa.Column("quality_summary", sa.String(length=40), nullable=False, server_default="VALID"),
        sa.Column("migration_classification", sa.String(length=40), nullable=True),
        sa.Column("legacy_table", sa.String(length=80), nullable=True),
        sa.Column("legacy_row_id", sa.Integer(), nullable=True),
        sa.Column("migration_batch_id", sa.String(length=80), nullable=True),
        sa.Column("mapping_rule_version", sa.String(length=40), nullable=True),
        sa.Column("migrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("device_id", "boot_id", "sequence", name="uq_telemetry_events_device_boot_sequence"),
    )
    for column in (
        "company_id",
        "storage_unit_id",
        "device_id",
        "gateway_id",
        "sensor_reading_id",
        "iot_reading_id",
        "sampled_at",
        "received_at_cloud",
        "raw_payload_hash",
        "quality_summary",
        "migration_classification",
        "migration_batch_id",
    ):
        op.create_index(f"ix_telemetry_events_{column}", "telemetry_events", [column])
    op.create_index("ix_telemetry_events_device_sampled", "telemetry_events", ["device_id", "sampled_at"])
    op.create_index("ix_telemetry_events_company_sampled", "telemetry_events", ["company_id", "sampled_at"])

    op.create_table(
        "metric_readings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telemetry_event_id", sa.Integer(), sa.ForeignKey("telemetry_events.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("sensor_channel_id", sa.Integer(), sa.ForeignKey("device_channels.id"), nullable=False),
        sa.Column("metric_definition_id", sa.Integer(), sa.ForeignKey("metric_definitions.id"), nullable=False),
        sa.Column("calibration_id", sa.Integer(), sa.ForeignKey("sensor_calibrations.id"), nullable=True),
        sa.Column("metric_code", sa.String(length=80), nullable=False),
        sa.Column("raw_value", sa.Float(), nullable=False),
        sa.Column("calibrated_value", sa.Float(), nullable=True),
        sa.Column("display_value", sa.Float(), nullable=True),
        sa.Column("canonical_unit", sa.String(length=24), nullable=False),
        sa.Column("quality_status", sa.String(length=40), nullable=False, server_default="VALID"),
        sa.Column("calibration_version", sa.Integer(), nullable=True),
        sa.Column("source_metric_code", sa.String(length=80), nullable=True),
        sa.Column("derivation_version", sa.String(length=40), nullable=True),
        sa.Column("sampled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("legacy_table", sa.String(length=80), nullable=True),
        sa.Column("legacy_row_id", sa.Integer(), nullable=True),
        sa.Column("migration_batch_id", sa.String(length=80), nullable=True),
        sa.Column("mapping_rule_version", sa.String(length=40), nullable=True),
        sa.Column("migrated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "telemetry_event_id",
            "sensor_channel_id",
            "metric_code",
            name="uq_metric_readings_event_channel_metric",
        ),
    )
    for column in (
        "telemetry_event_id",
        "company_id",
        "storage_unit_id",
        "device_id",
        "sensor_channel_id",
        "metric_definition_id",
        "calibration_id",
        "metric_code",
        "quality_status",
        "sampled_at",
        "migration_batch_id",
    ):
        op.create_index(f"ix_metric_readings_{column}", "metric_readings", [column])
    op.create_index("ix_metric_readings_series", "metric_readings", ["device_id", "metric_code", "sampled_at"])
    op.create_index(
        "ix_metric_readings_company_series",
        "metric_readings",
        ["company_id", "metric_code", "sampled_at"],
    )

    op.create_table(
        "device_dashboard_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("sensor_channel_id", sa.Integer(), sa.ForeignKey("device_channels.id"), nullable=False),
        sa.Column("metric_code", sa.String(length=80), nullable=False),
        sa.Column("chart_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("client_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chart_type_override", sa.String(length=32), nullable=True),
        sa.Column("display_name_override", sa.String(length=120), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "device_id",
            "sensor_channel_id",
            "metric_code",
            name="uq_device_dashboard_preference",
        ),
    )
    for column in ("device_id", "sensor_channel_id", "metric_code", "updated_by_id"):
        op.create_index(
            f"ix_device_dashboard_preferences_{column}",
            "device_dashboard_preferences",
            [column],
        )

    op.create_table(
        "legacy_migration_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.String(length=80), nullable=False),
        sa.Column("mapping_rule_version", sa.String(length=40), nullable=False),
        sa.Column("source_table", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="CREATED"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("original_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("safe_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requires_mapping_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quarantined_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_checksum", sa.String(length=64), nullable=True),
        sa.Column("reconciliation_json", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("batch_id", name="uq_legacy_migration_batches_batch_id"),
    )
    op.create_index("ix_legacy_migration_batches_batch_id", "legacy_migration_batches", ["batch_id"], unique=True)
    op.create_index("ix_legacy_migration_batches_status", "legacy_migration_batches", ["status"])

    op.create_table(
        "legacy_mapping_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("migration_batch_id", sa.String(length=80), nullable=False),
        sa.Column("legacy_table", sa.String(length=80), nullable=False),
        sa.Column("legacy_row_id", sa.Integer(), nullable=False),
        sa.Column("legacy_field", sa.String(length=80), nullable=False),
        sa.Column("classification", sa.String(length=40), nullable=False),
        sa.Column("device_type", sa.String(length=80), nullable=True),
        sa.Column("sensor_type", sa.String(length=80), nullable=True),
        sa.Column("channel_key", sa.String(length=80), nullable=True),
        sa.Column("metric_code", sa.String(length=80), nullable=True),
        sa.Column("canonical_unit", sa.String(length=24), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("raw_value_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "migration_batch_id",
            "legacy_table",
            "legacy_row_id",
            "legacy_field",
            name="uq_legacy_mapping_result",
        ),
    )
    for column in ("migration_batch_id", "legacy_table", "legacy_row_id", "classification"):
        op.create_index(f"ix_legacy_mapping_results_{column}", "legacy_mapping_results", [column])

    with op.batch_alter_table("threshold_configs") as batch:
        batch.add_column(sa.Column("device_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("sensor_channel_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("metric_definition_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"))
        batch.create_foreign_key("fk_threshold_configs_device_id", "devices", ["device_id"], ["id"])
        batch.create_foreign_key(
            "fk_threshold_configs_sensor_channel_id",
            "device_channels",
            ["sensor_channel_id"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_threshold_configs_metric_definition_id",
            "metric_definitions",
            ["metric_definition_id"],
            ["id"],
        )
        batch.create_index("ix_threshold_configs_device_id", ["device_id"])
        batch.create_index("ix_threshold_configs_sensor_channel_id", ["sensor_channel_id"])
        batch.create_index("ix_threshold_configs_metric_definition_id", ["metric_definition_id"])


def downgrade() -> None:
    # Downgrade removes only P1.5 structures. Legacy readings are never changed.
    with op.batch_alter_table("threshold_configs") as batch:
        batch.drop_index("ix_threshold_configs_metric_definition_id")
        batch.drop_index("ix_threshold_configs_sensor_channel_id")
        batch.drop_index("ix_threshold_configs_device_id")
        batch.drop_constraint("fk_threshold_configs_metric_definition_id", type_="foreignkey")
        batch.drop_constraint("fk_threshold_configs_sensor_channel_id", type_="foreignkey")
        batch.drop_constraint("fk_threshold_configs_device_id", type_="foreignkey")
        batch.drop_column("duration_seconds")
        batch.drop_column("metric_definition_id")
        batch.drop_column("sensor_channel_id")
        batch.drop_column("device_id")

    op.drop_table("legacy_mapping_results")
    op.drop_table("legacy_migration_batches")
    op.drop_table("device_dashboard_preferences")
    op.drop_table("metric_readings")
    op.drop_table("telemetry_events")

    with op.batch_alter_table("device_channels") as batch:
        batch.drop_constraint("uq_device_channels_device_channel_key", type_="unique")
        batch.drop_index("ix_device_channels_retired_by_id")
        batch.drop_index("ix_device_channels_status")
        batch.drop_index("ix_device_channels_is_enabled")
        batch.drop_index("ix_device_channels_is_installed")
        batch.drop_index("ix_device_channels_channel_key")
        batch.drop_constraint("fk_device_channels_retired_by_id", type_="foreignkey")
        batch.drop_column("updated_at")
        batch.drop_column("retirement_reason")
        batch.drop_column("retired_by_id")
        batch.drop_column("retired_at")
        batch.drop_column("last_valid_reading_at")
        batch.drop_column("display_order")
        batch.drop_column("display_name")
        batch.drop_column("status")
        batch.drop_column("calibration_required")
        batch.drop_column("alert_enabled")
        batch.drop_column("chart_enabled")
        batch.drop_column("is_visible_to_client")
        batch.drop_column("is_required")
        batch.drop_column("is_enabled")
        batch.drop_column("is_installed")
        batch.drop_column("canonical_unit")
        batch.drop_column("metric_codes")
        batch.drop_column("hardware_port")
        batch.drop_column("sensor_type")
        batch.drop_column("channel_key")

    with op.batch_alter_table("devices") as batch:
        batch.drop_index("ix_devices_template_code")
        batch.drop_column("capabilities_version")
        batch.drop_column("template_code")

    op.drop_table("metric_definitions")
