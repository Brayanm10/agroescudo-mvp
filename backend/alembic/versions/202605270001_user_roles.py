"""add user roles

Revision ID: 202605270001
Revises: 202605260002
Create Date: 2026-05-27 00:01:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605270001"
down_revision: Union[str, None] = "202605260002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "role" not in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column("role", sa.String(length=24), nullable=False, server_default="client")
            )

    op.execute("UPDATE users SET role = 'admin' WHERE email = 'admin@agroescudo.local'")
    op.execute("UPDATE users SET role = 'technician' WHERE email = 'tecnico@agroescudo.local'")
    op.execute("UPDATE users SET role = 'client' WHERE email = 'cliente@silo-demo.local'")

    if "ix_users_role" not in indexes:
        op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    indexes = {index["name"] for index in inspector.get_indexes("users")}

    if "ix_users_role" in indexes:
        op.drop_index(op.f("ix_users_role"), table_name="users")
    if "role" in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("role")
