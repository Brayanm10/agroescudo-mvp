"""dashboard api schema compatibility

Revision ID: 202605260002
Revises: 202605260001
Create Date: 2026-05-26 00:02:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605260002"
down_revision: Union[str, None] = "202605260001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    alert_columns = {column["name"] for column in inspector.get_columns("alerts")}
    alert_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("alerts")}
    if "uq_alert_active_device_type" in alert_constraints:
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.drop_constraint("uq_alert_active_device_type", type_="unique")
    if "resolved_at" not in alert_columns:
        op.add_column("alerts", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))

    log_columns = {column["name"] for column in inspector.get_columns("operational_logs")}
    if "alert_id" not in log_columns:
        op.add_column("operational_logs", sa.Column("alert_id", sa.Integer(), nullable=True))
        op.create_index(op.f("ix_operational_logs_alert_id"), "operational_logs", ["alert_id"], unique=False)
    if "action_taken" not in log_columns:
        op.add_column("operational_logs", sa.Column("action_taken", sa.String(length=160), nullable=True))
        if "event_type" in log_columns:
            op.execute("UPDATE operational_logs SET action_taken = event_type")
    if "operator_name" not in log_columns:
        op.add_column("operational_logs", sa.Column("operator_name", sa.String(length=160), nullable=True))
        op.execute("UPDATE operational_logs SET operator_name = 'Sistema'")
    if "timestamp" not in log_columns:
        op.add_column("operational_logs", sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True))
        op.execute("UPDATE operational_logs SET timestamp = created_at")


def downgrade() -> None:
    pass
