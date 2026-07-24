"""node telemetry and ultrasonic level

Revision ID: 202607220001
Revises: 202607030001
Create Date: 2026-07-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607220001"
down_revision: Union[str, None] = "202607030001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("devices") as batch:
        batch.add_column(sa.Column("empty_distance_cm", sa.Float(), nullable=True))
        batch.add_column(sa.Column("full_distance_cm", sa.Float(), nullable=True))

    with op.batch_alter_table("sensor_readings") as batch:
        batch.alter_column("grain_temperature", existing_type=sa.Float(), nullable=True)
        batch.alter_column("ambient_temperature", existing_type=sa.Float(), nullable=True)
        batch.alter_column("ambient_humidity", existing_type=sa.Float(), nullable=True)
        batch.alter_column("battery_voltage", existing_type=sa.Float(), nullable=True)
        batch.alter_column("signal_quality", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("level_distance_cm", sa.Float(), nullable=True))
        batch.add_column(sa.Column("level_percent", sa.Float(), nullable=True))
        batch.add_column(sa.Column("soil_moisture_percent", sa.Float(), nullable=True))
        batch.add_column(sa.Column("soil_temperature_c", sa.Float(), nullable=True))
        batch.add_column(sa.Column("sensor_status", sa.Integer(), nullable=True))
        batch.create_index("ix_sensor_readings_device_timestamp", ["device_id", "timestamp"])

    with op.batch_alter_table("iot_readings") as batch:
        batch.alter_column("grain_temp_c_x100", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("air_temp_c_x100", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("rh_x100", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("battery_mv", existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column("soil_moisture_x100", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("soil_temp_c_x100", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("level_distance_mm", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("level_percent_x100", sa.Integer(), nullable=True))

    with op.batch_alter_table("alerts") as batch:
        batch.add_column(sa.Column("metric", sa.String(length=80), nullable=True))
        batch.add_column(sa.Column("observed_value", sa.Float(), nullable=True))
        batch.add_column(sa.Column("threshold_value", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("alerts") as batch:
        batch.drop_column("threshold_value")
        batch.drop_column("observed_value")
        batch.drop_column("metric")

    with op.batch_alter_table("iot_readings") as batch:
        batch.drop_column("level_percent_x100")
        batch.drop_column("level_distance_mm")
        batch.drop_column("soil_temp_c_x100")
        batch.drop_column("soil_moisture_x100")
        batch.alter_column("battery_mv", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("rh_x100", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("air_temp_c_x100", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("grain_temp_c_x100", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("sensor_readings") as batch:
        batch.drop_index("ix_sensor_readings_device_timestamp")
        batch.drop_column("sensor_status")
        batch.drop_column("soil_temperature_c")
        batch.drop_column("soil_moisture_percent")
        batch.drop_column("level_percent")
        batch.drop_column("level_distance_cm")
        batch.alter_column("signal_quality", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("battery_voltage", existing_type=sa.Float(), nullable=False)
        batch.alter_column("ambient_humidity", existing_type=sa.Float(), nullable=False)
        batch.alter_column("ambient_temperature", existing_type=sa.Float(), nullable=False)
        batch.alter_column("grain_temperature", existing_type=sa.Float(), nullable=False)

    with op.batch_alter_table("devices") as batch:
        batch.drop_column("full_distance_cm")
        batch.drop_column("empty_distance_cm")
