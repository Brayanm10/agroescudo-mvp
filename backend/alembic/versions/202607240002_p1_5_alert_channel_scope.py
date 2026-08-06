"""Scope P1.5 alerts to canonical channels and metrics.

Revision ID: 202607240002
Revises: 202607240001
"""

from alembic import op
import sqlalchemy as sa


revision = "202607240002"
down_revision = "202607240001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("alerts") as batch:
        batch.add_column(sa.Column("sensor_channel_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("metric_definition_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_alerts_sensor_channel_id_device_channels",
            "device_channels",
            ["sensor_channel_id"],
            ["id"],
        )
        batch.create_foreign_key(
            "fk_alerts_metric_definition_id_metric_definitions",
            "metric_definitions",
            ["metric_definition_id"],
            ["id"],
        )
        batch.create_index("ix_alerts_sensor_channel_id", ["sensor_channel_id"])
        batch.create_index("ix_alerts_metric_definition_id", ["metric_definition_id"])


def downgrade() -> None:
    with op.batch_alter_table("alerts") as batch:
        batch.drop_index("ix_alerts_metric_definition_id")
        batch.drop_index("ix_alerts_sensor_channel_id")
        batch.drop_constraint(
            "fk_alerts_metric_definition_id_metric_definitions", type_="foreignkey"
        )
        batch.drop_constraint(
            "fk_alerts_sensor_channel_id_device_channels", type_="foreignkey"
        )
        batch.drop_column("metric_definition_id")
        batch.drop_column("sensor_channel_id")
