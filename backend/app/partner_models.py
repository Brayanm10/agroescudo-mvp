"""Additive partner API persistence, independent of human accounts and JWTs."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PartnerClient(Base):
    __tablename__ = "partner_clients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[str] = mapped_column(String(128), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    scopes: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PartnerCredential(Base):
    __tablename__ = "partner_credentials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("partner_clients.id"), index=True)
    secret_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PartnerToken(Base):
    __tablename__ = "partner_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("partner_clients.id"), index=True)
    credential_id: Mapped[int] = mapped_column(ForeignKey("partner_credentials.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scopes: Mapped[str] = mapped_column(String(200))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PartnerOrganization(Base):
    __tablename__ = "partner_organizations"
    __table_args__ = (UniqueConstraint("client_id", "external_id", name="uq_partner_org_external"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("partner_clients.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(128))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PartnerProducer(Base):
    __tablename__ = "partner_producers"
    __table_args__ = (UniqueConstraint("organization_id", "external_id", name="uq_partner_producer_external"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("partner_organizations.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(128))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PartnerGrant(Base):
    __tablename__ = "partner_grants"
    __table_args__ = (CheckConstraint("channel_key IS NULL OR device_id IS NOT NULL", name="ck_partner_channel_device"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producer_id: Mapped[int] = mapped_column(ForeignKey("partner_producers.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), index=True)
    channel_key: Mapped[str | None] = mapped_column(String(80))
    approved_by: Mapped[str] = mapped_column(String(160))
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PartnerAudit(Base):
    __tablename__ = "partner_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    client_id: Mapped[str | None] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(String(80))
    resource: Mapped[str | None] = mapped_column(String(200))
    status_code: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latency_ms: Mapped[float] = mapped_column(Float)


class PartnerBucket(Base):
    __tablename__ = "partner_buckets"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    balance: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=0)
