"""iot batch ingestion

Revision ID: 202607010001
Revises: 202606180002
Create Date: 2026-07-01 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202607010001"
down_revision: Union[str, None] = "202606180002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iot_gateways",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gateway_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("firmware_version", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gateway_id"),
    )
    op.create_index("ix_iot_gateways_gateway_id", "iot_gateways", ["gateway_id"])
    op.create_index("ix_iot_gateways_is_active", "iot_gateways", ["is_active"])

    op.create_table(
        "iot_gateway_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gateway_id", sa.Integer(), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("secret_hash", sa.String(length=255), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["gateway_id"], ["iot_gateways.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gateway_id", "key_version", name="uq_iot_gateway_credentials_gateway_key_version"),
    )
    op.create_index("ix_iot_gateway_credentials_gateway_id", "iot_gateway_credentials", ["gateway_id"])
    op.create_index("ix_iot_gateway_credentials_is_active", "iot_gateway_credentials", ["is_active"])

    op.create_table(
        "iot_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("firmware_version", sa.String(length=40), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id"),
    )
    op.create_index("ix_iot_devices_node_id", "iot_devices", ["node_id"])
    op.create_index("ix_iot_devices_device_id", "iot_devices", ["device_id"])
    op.create_index("ix_iot_devices_is_active", "iot_devices", ["is_active"])

    op.create_table(
        "iot_ingestion_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gateway_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.String(length=120), nullable=False),
        sa.Column("nonce", sa.String(length=160), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gateway_id"], ["iot_gateways.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id"),
        sa.UniqueConstraint("gateway_id", "nonce", name="uq_iot_ingestion_batches_gateway_nonce"),
    )
    op.create_index("ix_iot_ingestion_batches_batch_id", "iot_ingestion_batches", ["batch_id"])
    op.create_index("ix_iot_ingestion_batches_gateway_id", "iot_ingestion_batches", ["gateway_id"])
    op.create_index("ix_iot_ingestion_batches_nonce", "iot_ingestion_batches", ["nonce"])
    op.create_index("ix_iot_ingestion_batches_sent_at", "iot_ingestion_batches", ["sent_at"])
    op.create_index("ix_iot_ingestion_batches_status", "iot_ingestion_batches", ["status"])

    op.create_table(
        "iot_readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("iot_device_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("gateway_id", sa.Integer(), nullable=False),
        sa.Column("sensor_reading_id", sa.Integer(), nullable=True),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), nullable=False),
        sa.Column("boot_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("sample_counter", sa.Integer(), nullable=False),
        sa.Column("timestamp_utc", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("time_quality", sa.Integer(), nullable=False),
        sa.Column("grain_temp_c_x100", sa.Integer(), nullable=False),
        sa.Column("air_temp_c_x100", sa.Integer(), nullable=False),
        sa.Column("rh_x100", sa.Integer(), nullable=False),
        sa.Column("battery_mv", sa.Integer(), nullable=False),
        sa.Column("sensor_status", sa.Integer(), nullable=False),
        sa.Column("firmware_version", sa.Integer(), nullable=False),
        sa.Column("rssi_dbm", sa.Integer(), nullable=True),
        sa.Column("snr_db_x10", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["gateway_id"], ["iot_gateways.id"]),
        sa.ForeignKeyConstraint(["iot_device_id"], ["iot_devices.id"]),
        sa.ForeignKeyConstraint(["sensor_reading_id"], ["sensor_readings.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["storage_unit_id"], ["storage_units.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iot_device_id", "boot_id", "sequence", name="uq_iot_readings_device_boot_sequence"),
    )
    op.create_index("ix_iot_readings_company_id", "iot_readings", ["company_id"])
    op.create_index("ix_iot_readings_device_id", "iot_readings", ["device_id"])
    op.create_index("ix_iot_readings_gateway_id", "iot_readings", ["gateway_id"])
    op.create_index("ix_iot_readings_iot_device_id", "iot_readings", ["iot_device_id"])
    op.create_index("ix_iot_readings_sensor_reading_id", "iot_readings", ["sensor_reading_id"])
    op.create_index("ix_iot_readings_site_id", "iot_readings", ["site_id"])
    op.create_index("ix_iot_readings_storage_unit_id", "iot_readings", ["storage_unit_id"])
    op.create_index("ix_iot_readings_timestamp", "iot_readings", ["timestamp"])
    op.create_index("ix_iot_readings_device_timestamp", "iot_readings", ["iot_device_id", "timestamp"])
    op.create_index("ix_iot_readings_gateway_timestamp", "iot_readings", ["gateway_id", "timestamp"])
    op.create_index("ix_iot_readings_storage_timestamp", "iot_readings", ["storage_unit_id", "timestamp"])

    op.create_table(
        "iot_ingestion_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("gateway_id", sa.Integer(), nullable=False),
        sa.Column("iot_device_id", sa.Integer(), nullable=True),
        sa.Column("device_identifier", sa.Integer(), nullable=False),
        sa.Column("boot_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["iot_ingestion_batches.id"]),
        sa.ForeignKeyConstraint(["gateway_id"], ["iot_gateways.id"]),
        sa.ForeignKeyConstraint(["iot_device_id"], ["iot_devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_iot_ingestion_events_batch_id", "iot_ingestion_events", ["batch_id"])
    op.create_index("ix_iot_ingestion_events_gateway_id", "iot_ingestion_events", ["gateway_id"])
    op.create_index("ix_iot_ingestion_events_iot_device_id", "iot_ingestion_events", ["iot_device_id"])
    op.create_index("ix_iot_ingestion_events_device_identifier", "iot_ingestion_events", ["device_identifier"])
    op.create_index("ix_iot_ingestion_events_status", "iot_ingestion_events", ["status"])
    op.create_index("ix_iot_ingestion_events_status_created", "iot_ingestion_events", ["status", "created_at"])

    op.create_table(
        "iot_gateway_health",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gateway_id", sa.Integer(), nullable=False),
        sa.Column("firmware_version", sa.String(length=40), nullable=True),
        sa.Column("queue_depth", sa.Integer(), nullable=True),
        sa.Column("free_heap", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["gateway_id"], ["iot_gateways.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_iot_gateway_health_gateway_id", "iot_gateway_health", ["gateway_id"])
    op.create_index("ix_iot_gateway_health_recorded_at", "iot_gateway_health", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_iot_gateway_health_recorded_at", table_name="iot_gateway_health")
    op.drop_index("ix_iot_gateway_health_gateway_id", table_name="iot_gateway_health")
    op.drop_table("iot_gateway_health")

    op.drop_index("ix_iot_ingestion_events_status_created", table_name="iot_ingestion_events")
    op.drop_index("ix_iot_ingestion_events_status", table_name="iot_ingestion_events")
    op.drop_index("ix_iot_ingestion_events_device_identifier", table_name="iot_ingestion_events")
    op.drop_index("ix_iot_ingestion_events_iot_device_id", table_name="iot_ingestion_events")
    op.drop_index("ix_iot_ingestion_events_gateway_id", table_name="iot_ingestion_events")
    op.drop_index("ix_iot_ingestion_events_batch_id", table_name="iot_ingestion_events")
    op.drop_table("iot_ingestion_events")

    op.drop_index("ix_iot_readings_storage_timestamp", table_name="iot_readings")
    op.drop_index("ix_iot_readings_gateway_timestamp", table_name="iot_readings")
    op.drop_index("ix_iot_readings_device_timestamp", table_name="iot_readings")
    op.drop_index("ix_iot_readings_timestamp", table_name="iot_readings")
    op.drop_index("ix_iot_readings_storage_unit_id", table_name="iot_readings")
    op.drop_index("ix_iot_readings_site_id", table_name="iot_readings")
    op.drop_index("ix_iot_readings_sensor_reading_id", table_name="iot_readings")
    op.drop_index("ix_iot_readings_iot_device_id", table_name="iot_readings")
    op.drop_index("ix_iot_readings_gateway_id", table_name="iot_readings")
    op.drop_index("ix_iot_readings_device_id", table_name="iot_readings")
    op.drop_index("ix_iot_readings_company_id", table_name="iot_readings")
    op.drop_table("iot_readings")

    op.drop_index("ix_iot_ingestion_batches_status", table_name="iot_ingestion_batches")
    op.drop_index("ix_iot_ingestion_batches_sent_at", table_name="iot_ingestion_batches")
    op.drop_index("ix_iot_ingestion_batches_nonce", table_name="iot_ingestion_batches")
    op.drop_index("ix_iot_ingestion_batches_gateway_id", table_name="iot_ingestion_batches")
    op.drop_index("ix_iot_ingestion_batches_batch_id", table_name="iot_ingestion_batches")
    op.drop_table("iot_ingestion_batches")

    op.drop_index("ix_iot_devices_is_active", table_name="iot_devices")
    op.drop_index("ix_iot_devices_device_id", table_name="iot_devices")
    op.drop_index("ix_iot_devices_node_id", table_name="iot_devices")
    op.drop_table("iot_devices")

    op.drop_index("ix_iot_gateway_credentials_is_active", table_name="iot_gateway_credentials")
    op.drop_index("ix_iot_gateway_credentials_gateway_id", table_name="iot_gateway_credentials")
    op.drop_table("iot_gateway_credentials")

    op.drop_index("ix_iot_gateways_is_active", table_name="iot_gateways")
    op.drop_index("ix_iot_gateways_gateway_id", table_name="iot_gateways")
    op.drop_table("iot_gateways")
