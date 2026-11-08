"""Add isolated partner service, grants, tokens, SQL quotas and audit tables.

Additive only. Existing telemetry and human authentication are unchanged.
"""
from alembic import op
import sqlalchemy as sa

revision = "202611070001"
down_revision = "202610100002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('partner_audit',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('request_id', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('client_id', sa.String(length=128), nullable=True, primary_key=False),
        sa.Column('action', sa.String(length=80), nullable=False, primary_key=False),
        sa.Column('resource', sa.String(length=200), nullable=True, primary_key=False),
        sa.Column('status_code', sa.Integer(), nullable=False, primary_key=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('latency_ms', sa.Float(), nullable=False, primary_key=False),
    )
    op.create_index('ix_partner_audit_client_id', 'partner_audit', ['client_id'], unique=False)
    op.create_index('ix_partner_audit_occurred_at', 'partner_audit', ['occurred_at'], unique=False)
    op.create_index('ix_partner_audit_request_id', 'partner_audit', ['request_id'], unique=False)
    op.create_table('partner_buckets',
        sa.Column('key', sa.String(length=100), nullable=False, primary_key=True),
        sa.Column('balance', sa.Float(), nullable=False, primary_key=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('version', sa.Integer(), nullable=False, primary_key=False),
    )
    op.create_table('partner_clients',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('client_id', sa.String(length=128), nullable=False, primary_key=False),
        sa.Column('name', sa.String(length=160), nullable=False, primary_key=False),
        sa.Column('scopes', sa.String(length=200), nullable=False, primary_key=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, primary_key=False),
        sa.Column('is_demo', sa.Boolean(), nullable=False, primary_key=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True, primary_key=False),
        sa.UniqueConstraint('client_id', name=None),
    )
    op.create_table('partner_credentials',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('partner_clients.id'), nullable=False, primary_key=False),
        sa.Column('secret_hash', sa.String(length=255), nullable=False, primary_key=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, primary_key=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True, primary_key=False),
    )
    op.create_index('ix_partner_credentials_client_id', 'partner_credentials', ['client_id'], unique=False)
    op.create_table('partner_organizations',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('partner_clients.id'), nullable=False, primary_key=False),
        sa.Column('external_id', sa.String(length=128), nullable=False, primary_key=False),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False, primary_key=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True, primary_key=False),
        sa.UniqueConstraint('client_id', 'external_id', name='uq_partner_org_external'),
    )
    op.create_index('ix_partner_organizations_client_id', 'partner_organizations', ['client_id'], unique=False)
    op.create_index('ix_partner_organizations_company_id', 'partner_organizations', ['company_id'], unique=False)
    op.create_table('partner_producers',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('partner_organizations.id'), nullable=False, primary_key=False),
        sa.Column('external_id', sa.String(length=128), nullable=False, primary_key=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True, primary_key=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True, primary_key=False),
        sa.UniqueConstraint('organization_id', 'external_id', name='uq_partner_producer_external'),
    )
    op.create_index('ix_partner_producers_organization_id', 'partner_producers', ['organization_id'], unique=False)
    op.create_table('partner_tokens',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('partner_clients.id'), nullable=False, primary_key=False),
        sa.Column('credential_id', sa.Integer(), sa.ForeignKey('partner_credentials.id'), nullable=False, primary_key=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False, primary_key=False),
        sa.Column('scopes', sa.String(length=200), nullable=False, primary_key=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True, primary_key=False),
        sa.UniqueConstraint('token_hash', name=None),
    )
    op.create_index('ix_partner_tokens_client_id', 'partner_tokens', ['client_id'], unique=False)
    op.create_index('ix_partner_tokens_credential_id', 'partner_tokens', ['credential_id'], unique=False)
    op.create_index('ix_partner_tokens_expires_at', 'partner_tokens', ['expires_at'], unique=False)
    op.create_table('partner_grants',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('producer_id', sa.Integer(), sa.ForeignKey('partner_producers.id'), nullable=False, primary_key=False),
        sa.Column('storage_unit_id', sa.Integer(), sa.ForeignKey('storage_units.id'), nullable=False, primary_key=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=True, primary_key=False),
        sa.Column('channel_key', sa.String(length=80), nullable=True, primary_key=False),
        sa.Column('approved_by', sa.String(length=160), nullable=False, primary_key=False),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False, primary_key=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, primary_key=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True, primary_key=False),
        sa.CheckConstraint('channel_key IS NULL OR device_id IS NOT NULL', name='ck_partner_channel_device'),
    )
    op.create_index('ix_partner_grants_device_id', 'partner_grants', ['device_id'], unique=False)
    op.create_index('ix_partner_grants_producer_id', 'partner_grants', ['producer_id'], unique=False)
    op.create_index('ix_partner_grants_storage_unit_id', 'partner_grants', ['storage_unit_id'], unique=False)


def downgrade():
    # Explicit operator action only; never run downgrade against operational data.
    op.drop_table('partner_grants')
    op.drop_table('partner_tokens')
    op.drop_table('partner_producers')
    op.drop_table('partner_organizations')
    op.drop_table('partner_credentials')
    op.drop_table('partner_clients')
    op.drop_table('partner_buckets')
    op.drop_table('partner_audit')
