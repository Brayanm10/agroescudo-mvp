"""initial schema

Revision ID: 202605260001
Revises:
Create Date: 2026-05-26 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605260001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("tax_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_companies_name"), "companies", ["name"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_company_id"), "users", ["company_id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sites_company_id"), "sites", ["company_id"], unique=False)
    op.create_index(op.f("ix_sites_name"), "sites", ["name"], unique=False)

    op.create_table(
        "storage_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("unit_type", sa.String(length=40), nullable=False),
        sa.Column("capacity_tons", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_storage_units_company_id"), "storage_units", ["company_id"], unique=False)
    op.create_index(op.f("ix_storage_units_name"), "storage_units", ["name"], unique=False)
    op.create_index(op.f("ix_storage_units_site_id"), "storage_units", ["site_id"], unique=False)

    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["storage_unit_id"], ["storage_units.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_devices_company_id"), "devices", ["company_id"], unique=False)
    op.create_index(op.f("ix_devices_external_id"), "devices", ["external_id"], unique=True)
    op.create_index(op.f("ix_devices_site_id"), "devices", ["site_id"], unique=False)
    op.create_index(op.f("ix_devices_storage_unit_id"), "devices", ["storage_unit_id"], unique=False)

    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("grain_temperature", sa.Float(), nullable=False),
        sa.Column("ambient_temperature", sa.Float(), nullable=False),
        sa.Column("ambient_humidity", sa.Float(), nullable=False),
        sa.Column("battery_voltage", sa.Float(), nullable=False),
        sa.Column("signal_quality", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["storage_unit_id"], ["storage_units.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sensor_readings_company_id"), "sensor_readings", ["company_id"], unique=False)
    op.create_index(op.f("ix_sensor_readings_device_id"), "sensor_readings", ["device_id"], unique=False)
    op.create_index(op.f("ix_sensor_readings_site_id"), "sensor_readings", ["site_id"], unique=False)
    op.create_index(op.f("ix_sensor_readings_storage_unit_id"), "sensor_readings", ["storage_unit_id"], unique=False)
    op.create_index(op.f("ix_sensor_readings_timestamp"), "sensor_readings", ["timestamp"], unique=False)

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["reading_id"], ["sensor_readings.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["storage_unit_id"], ["storage_units.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_alert_type"), "alerts", ["alert_type"], unique=False)
    op.create_index(op.f("ix_alerts_company_id"), "alerts", ["company_id"], unique=False)
    op.create_index(op.f("ix_alerts_device_id"), "alerts", ["device_id"], unique=False)
    op.create_index(op.f("ix_alerts_is_active"), "alerts", ["is_active"], unique=False)
    op.create_index(op.f("ix_alerts_reading_id"), "alerts", ["reading_id"], unique=False)
    op.create_index(op.f("ix_alerts_severity"), "alerts", ["severity"], unique=False)
    op.create_index(op.f("ix_alerts_site_id"), "alerts", ["site_id"], unique=False)
    op.create_index(op.f("ix_alerts_storage_unit_id"), "alerts", ["storage_unit_id"], unique=False)

    op.create_table(
        "operational_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action_taken", sa.String(length=160), nullable=False),
        sa.Column("operator_name", sa.String(length=160), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["storage_unit_id"], ["storage_units.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operational_logs_alert_id"), "operational_logs", ["alert_id"], unique=False)
    op.create_index(op.f("ix_operational_logs_action_taken"), "operational_logs", ["action_taken"], unique=False)
    op.create_index(op.f("ix_operational_logs_company_id"), "operational_logs", ["company_id"], unique=False)
    op.create_index(op.f("ix_operational_logs_site_id"), "operational_logs", ["site_id"], unique=False)
    op.create_index(op.f("ix_operational_logs_storage_unit_id"), "operational_logs", ["storage_unit_id"], unique=False)
    op.create_index(op.f("ix_operational_logs_timestamp"), "operational_logs", ["timestamp"], unique=False)
    op.create_index(op.f("ix_operational_logs_user_id"), "operational_logs", ["user_id"], unique=False)

    op.create_table(
        "threshold_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=True),
        sa.Column("storage_unit_id", sa.Integer(), nullable=True),
        sa.Column("metric", sa.String(length=80), nullable=False),
        sa.Column("operator", sa.String(length=8), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["storage_unit_id"], ["storage_units.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_threshold_configs_company_id"), "threshold_configs", ["company_id"], unique=False)
    op.create_index(op.f("ix_threshold_configs_is_active"), "threshold_configs", ["is_active"], unique=False)
    op.create_index(op.f("ix_threshold_configs_metric"), "threshold_configs", ["metric"], unique=False)
    op.create_index(op.f("ix_threshold_configs_site_id"), "threshold_configs", ["site_id"], unique=False)
    op.create_index(op.f("ix_threshold_configs_storage_unit_id"), "threshold_configs", ["storage_unit_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_threshold_configs_storage_unit_id"), table_name="threshold_configs")
    op.drop_index(op.f("ix_threshold_configs_site_id"), table_name="threshold_configs")
    op.drop_index(op.f("ix_threshold_configs_metric"), table_name="threshold_configs")
    op.drop_index(op.f("ix_threshold_configs_is_active"), table_name="threshold_configs")
    op.drop_index(op.f("ix_threshold_configs_company_id"), table_name="threshold_configs")
    op.drop_table("threshold_configs")
    op.drop_index(op.f("ix_operational_logs_user_id"), table_name="operational_logs")
    op.drop_index(op.f("ix_operational_logs_timestamp"), table_name="operational_logs")
    op.drop_index(op.f("ix_operational_logs_storage_unit_id"), table_name="operational_logs")
    op.drop_index(op.f("ix_operational_logs_site_id"), table_name="operational_logs")
    op.drop_index(op.f("ix_operational_logs_company_id"), table_name="operational_logs")
    op.drop_index(op.f("ix_operational_logs_action_taken"), table_name="operational_logs")
    op.drop_index(op.f("ix_operational_logs_alert_id"), table_name="operational_logs")
    op.drop_table("operational_logs")
    op.drop_index(op.f("ix_alerts_storage_unit_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_site_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_severity"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_reading_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_is_active"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_device_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_company_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_alert_type"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(op.f("ix_sensor_readings_timestamp"), table_name="sensor_readings")
    op.drop_index(op.f("ix_sensor_readings_storage_unit_id"), table_name="sensor_readings")
    op.drop_index(op.f("ix_sensor_readings_site_id"), table_name="sensor_readings")
    op.drop_index(op.f("ix_sensor_readings_device_id"), table_name="sensor_readings")
    op.drop_index(op.f("ix_sensor_readings_company_id"), table_name="sensor_readings")
    op.drop_table("sensor_readings")
    op.drop_index(op.f("ix_devices_storage_unit_id"), table_name="devices")
    op.drop_index(op.f("ix_devices_site_id"), table_name="devices")
    op.drop_index(op.f("ix_devices_external_id"), table_name="devices")
    op.drop_index(op.f("ix_devices_company_id"), table_name="devices")
    op.drop_table("devices")
    op.drop_index(op.f("ix_storage_units_site_id"), table_name="storage_units")
    op.drop_index(op.f("ix_storage_units_name"), table_name="storage_units")
    op.drop_index(op.f("ix_storage_units_company_id"), table_name="storage_units")
    op.drop_table("storage_units")
    op.drop_index(op.f("ix_sites_name"), table_name="sites")
    op.drop_index(op.f("ix_sites_company_id"), table_name="sites")
    op.drop_table("sites")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_company_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_companies_name"), table_name="companies")
    op.drop_table("companies")
