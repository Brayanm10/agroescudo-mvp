"""add pilot operations fields

Revision ID: 202605310001
Revises: 202605270001
Create Date: 2026-05-31 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605310001"
down_revision: Union[str, None] = "202605270001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    storage_columns = {column["name"] for column in inspector.get_columns("storage_units")}
    storage_indexes = {index["name"] for index in inspector.get_indexes("storage_units")}
    with op.batch_alter_table("storage_units") as batch_op:
        if "assigned_technician_id" not in storage_columns:
            batch_op.add_column(sa.Column("assigned_technician_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_storage_units_assigned_technician_id_users",
                "users",
                ["assigned_technician_id"],
                ["id"],
            )
        if "assigned_client_id" not in storage_columns:
            batch_op.add_column(sa.Column("assigned_client_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_storage_units_assigned_client_id_users",
                "users",
                ["assigned_client_id"],
                ["id"],
            )
        if "last_report_generated_at" not in storage_columns:
            batch_op.add_column(sa.Column("last_report_generated_at", sa.DateTime(timezone=True), nullable=True))

    if "ix_storage_units_assigned_technician_id" not in storage_indexes:
        op.create_index(
            op.f("ix_storage_units_assigned_technician_id"),
            "storage_units",
            ["assigned_technician_id"],
            unique=False,
        )
    if "ix_storage_units_assigned_client_id" not in storage_indexes:
        op.create_index(
            op.f("ix_storage_units_assigned_client_id"),
            "storage_units",
            ["assigned_client_id"],
            unique=False,
        )

    log_columns = {column["name"] for column in inspector.get_columns("operational_logs")}
    log_indexes = {index["name"] for index in inspector.get_indexes("operational_logs")}
    with op.batch_alter_table("operational_logs") as batch_op:
        if "device_id" not in log_columns:
            batch_op.add_column(sa.Column("device_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_operational_logs_device_id_devices",
                "devices",
                ["device_id"],
                ["id"],
            )
        if "category" not in log_columns:
            batch_op.add_column(
                sa.Column(
                    "category",
                    sa.String(length=40),
                    nullable=False,
                    server_default="corrective_action",
                )
            )

    if "ix_operational_logs_device_id" not in log_indexes:
        op.create_index(op.f("ix_operational_logs_device_id"), "operational_logs", ["device_id"], unique=False)
    if "ix_operational_logs_category" not in log_indexes:
        op.create_index(op.f("ix_operational_logs_category"), "operational_logs", ["category"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    log_columns = {column["name"] for column in inspector.get_columns("operational_logs")}
    log_indexes = {index["name"] for index in inspector.get_indexes("operational_logs")}
    if "ix_operational_logs_category" in log_indexes:
        op.drop_index(op.f("ix_operational_logs_category"), table_name="operational_logs")
    if "ix_operational_logs_device_id" in log_indexes:
        op.drop_index(op.f("ix_operational_logs_device_id"), table_name="operational_logs")
    with op.batch_alter_table("operational_logs") as batch_op:
        if "category" in log_columns:
            batch_op.drop_column("category")
        if "device_id" in log_columns:
            batch_op.drop_constraint("fk_operational_logs_device_id_devices", type_="foreignkey")
            batch_op.drop_column("device_id")

    storage_columns = {column["name"] for column in inspector.get_columns("storage_units")}
    storage_indexes = {index["name"] for index in inspector.get_indexes("storage_units")}
    if "ix_storage_units_assigned_client_id" in storage_indexes:
        op.drop_index(op.f("ix_storage_units_assigned_client_id"), table_name="storage_units")
    if "ix_storage_units_assigned_technician_id" in storage_indexes:
        op.drop_index(op.f("ix_storage_units_assigned_technician_id"), table_name="storage_units")
    with op.batch_alter_table("storage_units") as batch_op:
        if "last_report_generated_at" in storage_columns:
            batch_op.drop_column("last_report_generated_at")
        if "assigned_client_id" in storage_columns:
            batch_op.drop_constraint("fk_storage_units_assigned_client_id_users", type_="foreignkey")
            batch_op.drop_column("assigned_client_id")
        if "assigned_technician_id" in storage_columns:
            batch_op.drop_constraint("fk_storage_units_assigned_technician_id_users", type_="foreignkey")
            batch_op.drop_column("assigned_technician_id")
