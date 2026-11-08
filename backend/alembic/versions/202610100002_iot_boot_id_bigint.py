"""Preserve unsigned ESP32 boot identities in signed PostgreSQL BIGINT.

Also reconciles an already widened production schema without rewriting data.
"""
from alembic import op
import sqlalchemy as sa

revision = "202610100002"
down_revision = "202610100001"
branch_labels = None
depends_on = None

TABLES = ("iot_readings", "telemetry_events", "iot_ingestion_events")


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        # Fail promptly rather than waiting behind live ingestion indefinitely.
        op.execute("SET LOCAL lock_timeout = '5s'")
        op.execute("SET LOCAL statement_timeout = '60s'")
    for table in TABLES:
        column = next(c for c in sa.inspect(connection).get_columns(table) if c["name"] == "boot_id")
        if isinstance(column["type"], sa.BigInteger):
            continue
        if not isinstance(column["type"], sa.Integer):
            raise RuntimeError(f"Unexpected boot_id type in {table}")
        with op.batch_alter_table(table) as batch:
            batch.alter_column("boot_id", existing_type=column["type"], type_=sa.BigInteger(),
                               existing_nullable=column["nullable"])


def downgrade():
    # Never truncate identities from accepted or durable pending ESP32 samples.
    raise RuntimeError("Irreversible boot_id widening: retain BIGINT to preserve sample identity")
