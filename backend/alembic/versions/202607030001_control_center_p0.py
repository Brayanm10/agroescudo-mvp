"""control center p0

Revision ID: 202607030001
Revises: 202607020001
Create Date: 2026-07-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607030001"
down_revision: Union[str, None] = "202607020001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_index(table: str, columns: list[str], name: str | None = None, unique: bool = False) -> None:
    op.create_index(name or op.f(f"ix_{table}_{'_'.join(columns)}"), table, columns, unique=unique)


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch:
        batch.add_column(sa.Column("approval_status", sa.String(length=32), nullable=False, server_default="APPROVED"))
        batch.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("approved_by_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("rejection_reason", sa.Text(), nullable=True))
        batch.create_foreign_key("fk_companies_approved_by_id_users", "users", ["approved_by_id"], ["id"])
        batch.create_index("ix_companies_approval_status", ["approval_status"])
        batch.create_index("ix_companies_approved_by_id", ["approved_by_id"])

    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("locale", sa.String(length=10), nullable=False, server_default="es"))
        batch.add_column(sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"))
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_users_status", ["status"])

    with op.batch_alter_table("sites") as batch:
        batch.add_column(sa.Column("latitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("longitude", sa.Float(), nullable=True))
        batch.add_column(sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/La_Paz"))
        batch.add_column(sa.Column("address", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("department", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("municipality", sa.String(length=120), nullable=True))

    op.create_table(
        "organization_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("requester_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("responsible_name", sa.String(length=160), nullable=False),
        sa.Column("work_email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("commercial_name", sa.String(length=160), nullable=False),
        sa.Column("legal_name", sa.String(length=160), nullable=True),
        sa.Column("tax_id", sa.String(length=64), nullable=True),
        sa.Column("sector", sa.String(length=80), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("department", sa.String(length=120), nullable=True),
        sa.Column("estimated_sites", sa.Integer(), nullable=True),
        sa.Column("estimated_storage_units", sa.Integer(), nullable=True),
        sa.Column("use_case", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="es"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("consent_terms", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_privacy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_marketing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ["company_id", "requester_user_id", "work_email", "status", "reviewed_by_id", "created_at"]:
        _create_index("organization_requests", [column])

    op.create_table(
        "user_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("invited_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("storage_unit_ids", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="INVITED"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_index("user_invites", ["token_hash"], unique=True)
    for column in ["company_id", "email", "role", "invited_by_id", "status", "expires_at"]:
        _create_index("user_invites", [column])

    for table_name in ["email_verification_tokens", "password_reset_tokens"]:
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(length=255), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        _create_index(table_name, ["user_id"])
        _create_index(table_name, ["token_hash"], unique=True)
        _create_index(table_name, ["expires_at"])

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("jti", sa.String(length=80), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    _create_index("user_sessions", ["user_id"])
    _create_index("user_sessions", ["jti"], unique=True)
    _create_index("user_sessions", ["expires_at"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=True),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ["company_id", "user_id", "action", "resource_type", "resource_id", "created_at"]:
        _create_index("audit_events", [column])

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("company_name", sa.String(length=160), nullable=False),
        sa.Column("position", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("interest", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="web"),
        sa.Column("consent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ["email", "source", "created_at"]:
        _create_index("leads", [column])

    op.create_table(
        "device_channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("zone", sa.String(length=120), nullable=True),
        sa.Column("level", sa.String(length=80), nullable=True),
        sa.Column("position_description", sa.String(length=255), nullable=True),
        sa.Column("channel", sa.String(length=80), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ["device_id", "code", "is_active"]:
        _create_index("device_channels", [column])

    op.create_table(
        "service_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id"), nullable=False),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("alert_id", sa.Integer(), sa.ForeignKey("alerts.id"), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("assigned_technician_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("opened_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ["company_id", "site_id", "storage_unit_id", "device_id", "alert_id", "priority", "status", "assigned_technician_id", "opened_by_id", "created_at"]:
        _create_index("service_cases", [column])

    op.create_table(
        "service_case_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_case_id", sa.Integer(), sa.ForeignKey("service_cases.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ["service_case_id", "user_id", "event_type", "created_at"]:
        _create_index("service_case_events", [column])

    op.create_table(
        "stored_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("storage_provider", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column("bucket", sa.String(length=160), nullable=True),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_index("stored_files", ["object_key"], unique=True)
    for column in ["company_id", "uploaded_by_id", "created_at"]:
        _create_index("stored_files", [column])

    op.create_table(
        "maintenance_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("service_case_id", sa.Integer(), sa.ForeignKey("service_cases.id"), nullable=False),
        sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id"), nullable=False),
        sa.Column("technician_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("actions_performed", sa.Text(), nullable=False),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ["service_case_id", "storage_unit_id", "technician_user_id", "status", "created_at"]:
        _create_index("maintenance_reports", [column])

    op.create_table(
        "maintenance_report_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("maintenance_report_id", sa.Integer(), sa.ForeignKey("maintenance_reports.id"), nullable=False),
        sa.Column("stored_file_id", sa.Integer(), sa.ForeignKey("stored_files.id"), nullable=False),
        sa.Column("photo_type", sa.String(length=40), nullable=False, server_default="evidence"),
        sa.Column("caption", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ["maintenance_report_id", "stored_file_id", "photo_type"]:
        _create_index("maintenance_report_photos", [column])

    op.create_table(
        "maintenance_signatures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("maintenance_report_id", sa.Integer(), sa.ForeignKey("maintenance_reports.id"), nullable=False),
        sa.Column("signer_name", sa.String(length=160), nullable=False),
        sa.Column("signer_role", sa.String(length=80), nullable=True),
        sa.Column("signature_file_id", sa.Integer(), sa.ForeignKey("stored_files.id"), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    _create_index("maintenance_signatures", ["maintenance_report_id"])
    _create_index("maintenance_signatures", ["signature_file_id"])

    op.create_table(
        "education_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("locale", sa.String(length=10), nullable=False, server_default="es"),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False, server_default="postcosecha"),
        sa.Column("translation_status", sa.String(length=32), nullable=False, server_default="VERIFIED"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    _create_index("education_articles", ["slug"], unique=True)
    for column in ["locale", "category", "translation_status", "is_published"]:
        _create_index("education_articles", [column])

    op.create_table(
        "education_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("education_articles.id"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "article_id", name="uq_education_progress_user_article"),
    )
    _create_index("education_progress", ["user_id"])
    _create_index("education_progress", ["article_id"])

    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id"), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="rules"),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ["company_id", "user_id", "storage_unit_id", "source", "created_at"]:
        _create_index("ai_conversations", [column])

    op.create_table(
        "ai_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("ai_conversations.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="rules"),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_name", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ["conversation_id", "user_id", "provider"]:
        _create_index("ai_usage", [column])

    op.create_table(
        "rate_limit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ["identifier", "action", "window_start"]:
        _create_index("rate_limit_events", [column])


def downgrade() -> None:
    for table_name in [
        "rate_limit_events",
        "ai_usage",
        "ai_conversations",
        "education_progress",
        "education_articles",
        "maintenance_signatures",
        "maintenance_report_photos",
        "maintenance_reports",
        "stored_files",
        "service_case_events",
        "service_cases",
        "device_channels",
        "leads",
        "audit_events",
        "user_sessions",
        "password_reset_tokens",
        "email_verification_tokens",
        "user_invites",
        "organization_requests",
    ]:
        op.drop_table(table_name)

    with op.batch_alter_table("sites") as batch:
        batch.drop_column("municipality")
        batch.drop_column("department")
        batch.drop_column("address")
        batch.drop_column("timezone")
        batch.drop_column("longitude")
        batch.drop_column("latitude")

    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_status")
        batch.drop_column("last_seen_at")
        batch.drop_column("password_changed_at")
        batch.drop_column("email_verified_at")
        batch.drop_column("status")
        batch.drop_column("locale")

    with op.batch_alter_table("companies") as batch:
        batch.drop_index("ix_companies_approved_by_id")
        batch.drop_index("ix_companies_approval_status")
        batch.drop_constraint("fk_companies_approved_by_id_users", type_="foreignkey")
        batch.drop_column("rejection_reason")
        batch.drop_column("approved_by_id")
        batch.drop_column("approved_at")
        batch.drop_column("approval_status")
