"""account profile fields

Revision ID: 202607020001
Revises: 202607010001
Create Date: 2026-07-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "202607020001"
down_revision = "202607010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("language", sa.String(length=10), nullable=False, server_default="es"))
    op.add_column("users", sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/La_Paz"))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "timezone")
    op.drop_column("users", "language")
