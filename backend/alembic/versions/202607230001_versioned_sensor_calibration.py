"""versioned sensor calibration and product experiences

Revision ID: 202607230001
Revises: 202607220001
Create Date: 2026-07-23 00:00:00.000000
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607230001"
down_revision: Union[str, None] = "202607220001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("storage_units") as batch:
        batch.add_column(sa.Column("operation_type", sa.String(length=20), nullable=False, server_default="storage"))
        batch.add_column(sa.Column("surface_hectares", sa.Float(), nullable=True))
        batch.create_index("ix_storage_units_operation_type", ["operation_type"])

    op.execute(
        sa.text(
            "UPDATE storage_units SET operation_type = 'field' "
            "WHERE lower(unit_type) IN ('field', 'campo', 'parcela', 'lote')"
        )
    )

    with op.batch_alter_table("devices") as batch:
        batch.add_column(sa.Column("model_version", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("physical_location", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("iot_readings") as batch:
        batch.add_column(sa.Column("soil_moisture_raw", sa.Integer(), nullable=True))

    with op.batch_alter_table("device_channels") as batch:
        batch.add_column(sa.Column("metric_type", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("unit", sa.String(length=24), nullable=True))
        batch.add_column(sa.Column("adc_min", sa.Float(), nullable=True))
        batch.add_column(sa.Column("adc_max", sa.Float(), nullable=True))
        batch.create_index("ix_device_channels_metric_type", ["metric_type"])
        batch.create_unique_constraint("uq_device_channels_device_code", ["device_id", "code"])

    op.create_table(
        "sensor_calibrations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("device_channel_id", sa.Integer(), sa.ForeignKey("device_channels.id"), nullable=True),
        sa.Column("variable_type", sa.String(length=80), nullable=False),
        sa.Column("method", sa.String(length=40), nullable=False),
        sa.Column("offset", sa.Float(), nullable=True),
        sa.Column("slope", sa.Float(), nullable=True),
        sa.Column("intercept", sa.Float(), nullable=True),
        sa.Column("dry_raw", sa.Float(), nullable=True),
        sa.Column("wet_raw", sa.Float(), nullable=True),
        sa.Column("dry_percent", sa.Float(), nullable=True),
        sa.Column("wet_percent", sa.Float(), nullable=True),
        sa.Column("parameters_json", sa.Text(), nullable=True),
        sa.Column("calibration_version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calibrated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reference_instrument", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "device_id",
            "device_channel_id",
            "variable_type",
            "calibration_version",
            name="uq_sensor_calibrations_version",
        ),
    )
    op.create_index("ix_sensor_calibrations_device_id", "sensor_calibrations", ["device_id"])
    op.create_index("ix_sensor_calibrations_device_channel_id", "sensor_calibrations", ["device_channel_id"])
    op.create_index("ix_sensor_calibrations_variable_type", "sensor_calibrations", ["variable_type"])
    op.create_index("ix_sensor_calibrations_is_active", "sensor_calibrations", ["is_active"])
    op.create_index("ix_sensor_calibrations_calibrated_at", "sensor_calibrations", ["calibrated_at"])
    op.create_index("ix_sensor_calibrations_calibrated_by_user_id", "sensor_calibrations", ["calibrated_by_user_id"])
    op.create_index(
        "ix_sensor_calibrations_lookup",
        "sensor_calibrations",
        ["device_id", "variable_type", "is_active"],
    )
    op.create_index(
        "uq_sensor_calibrations_active_device_variable",
        "sensor_calibrations",
        ["device_id", "variable_type"],
        unique=True,
        sqlite_where=sa.text("is_active = 1 AND device_channel_id IS NULL"),
        postgresql_where=sa.text("is_active = true AND device_channel_id IS NULL"),
    )
    op.create_index(
        "uq_sensor_calibrations_device_variable_version",
        "sensor_calibrations",
        ["device_id", "variable_type", "calibration_version"],
        unique=True,
        sqlite_where=sa.text("device_channel_id IS NULL"),
        postgresql_where=sa.text("device_channel_id IS NULL"),
    )
    op.create_index(
        "uq_sensor_calibrations_active_channel_variable",
        "sensor_calibrations",
        ["device_channel_id", "variable_type"],
        unique=True,
        sqlite_where=sa.text("is_active = 1 AND device_channel_id IS NOT NULL"),
        postgresql_where=sa.text("is_active = true AND device_channel_id IS NOT NULL"),
    )

    op.create_table(
        "sensor_metric_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sensor_reading_id", sa.Integer(), sa.ForeignKey("sensor_readings.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("device_channel_id", sa.Integer(), sa.ForeignKey("device_channels.id"), nullable=True),
        sa.Column("calibration_id", sa.Integer(), sa.ForeignKey("sensor_calibrations.id"), nullable=True),
        sa.Column("variable_type", sa.String(length=80), nullable=False),
        sa.Column("raw_value", sa.Float(), nullable=False),
        sa.Column("calibrated_value", sa.Float(), nullable=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("calibration_version_applied", sa.Integer(), nullable=True),
        sa.Column("quality_status", sa.String(length=40), nullable=False, server_default="raw"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "sensor_reading_id",
            "device_channel_id",
            "variable_type",
            name="uq_sensor_metric_values_reading_channel_variable",
        ),
    )
    op.create_index("ix_sensor_metric_values_sensor_reading_id", "sensor_metric_values", ["sensor_reading_id"])
    op.create_index("ix_sensor_metric_values_device_id", "sensor_metric_values", ["device_id"])
    op.create_index("ix_sensor_metric_values_device_channel_id", "sensor_metric_values", ["device_channel_id"])
    op.create_index("ix_sensor_metric_values_calibration_id", "sensor_metric_values", ["calibration_id"])
    op.create_index("ix_sensor_metric_values_variable_type", "sensor_metric_values", ["variable_type"])
    op.create_index("ix_sensor_metric_values_quality_status", "sensor_metric_values", ["quality_status"])
    op.create_index(
        "ix_sensor_metric_values_reading_variable",
        "sensor_metric_values",
        ["sensor_reading_id", "variable_type"],
    )
    op.create_index(
        "uq_sensor_metric_values_reading_variable_no_channel",
        "sensor_metric_values",
        ["sensor_reading_id", "variable_type"],
        unique=True,
        sqlite_where=sa.text("device_channel_id IS NULL"),
        postgresql_where=sa.text("device_channel_id IS NULL"),
    )

    connection = op.get_bind()
    devices = connection.execute(
        sa.text(
            "SELECT id, empty_distance_cm, full_distance_cm FROM devices "
            "WHERE empty_distance_cm IS NOT NULL AND full_distance_cm IS NOT NULL "
            "AND empty_distance_cm > full_distance_cm AND full_distance_cm > 0"
        )
    ).mappings()
    calibration_table = sa.table(
        "sensor_calibrations",
        sa.column("device_id", sa.Integer()),
        sa.column("device_channel_id", sa.Integer()),
        sa.column("variable_type", sa.String()),
        sa.column("method", sa.String()),
        sa.column("parameters_json", sa.Text()),
        sa.column("calibration_version", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
        sa.column("calibrated_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("notes", sa.Text()),
    )
    now = sa.func.now()
    for device in devices:
        connection.execute(
            calibration_table.insert().values(
                device_id=device["id"],
                device_channel_id=None,
                variable_type="level_percent",
                method="LEVEL_GEOMETRY",
                parameters_json=json.dumps(
                    {
                        "mode": "two_distance",
                        "empty_distance_cm": device["empty_distance_cm"],
                        "full_distance_cm": device["full_distance_cm"],
                        "mounting_offset_cm": 0,
                    }
                ),
                calibration_version=1,
                is_active=True,
                calibrated_at=now,
                created_at=now,
                notes="Migrada desde la calibracion ultrasónica compatible.",
            )
        )


def downgrade() -> None:
    op.drop_index("uq_sensor_metric_values_reading_variable_no_channel", table_name="sensor_metric_values")
    op.drop_index("ix_sensor_metric_values_reading_variable", table_name="sensor_metric_values")
    op.drop_table("sensor_metric_values")
    op.drop_index("uq_sensor_calibrations_active_channel_variable", table_name="sensor_calibrations")
    op.drop_index("uq_sensor_calibrations_active_device_variable", table_name="sensor_calibrations")
    op.drop_index("uq_sensor_calibrations_device_variable_version", table_name="sensor_calibrations")
    op.drop_index("ix_sensor_calibrations_lookup", table_name="sensor_calibrations")
    op.drop_table("sensor_calibrations")

    with op.batch_alter_table("device_channels") as batch:
        batch.drop_constraint("uq_device_channels_device_code", type_="unique")
        batch.drop_index("ix_device_channels_metric_type")
        batch.drop_column("adc_max")
        batch.drop_column("adc_min")
        batch.drop_column("unit")
        batch.drop_column("metric_type")

    with op.batch_alter_table("devices") as batch:
        batch.drop_column("installed_at")
        batch.drop_column("physical_location")
        batch.drop_column("model_version")

    with op.batch_alter_table("iot_readings") as batch:
        batch.drop_column("soil_moisture_raw")

    with op.batch_alter_table("storage_units") as batch:
        batch.drop_index("ix_storage_units_operation_type")
        batch.drop_column("surface_hectares")
        batch.drop_column("operation_type")
