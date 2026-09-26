from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CompanyFeature, User, utc_now
from app.services.audit import record_audit_event


PLUVIOMETRY = "PLUVIOMETRY"
FEATURE_CATALOG = (PLUVIOMETRY,)


def normalize_feature_code(feature_code: str) -> str:
    normalized = feature_code.strip().upper()
    if normalized not in FEATURE_CATALOG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="feature_not_found")
    return normalized


def is_feature_enabled(db: Session, company_id: int, feature_code: str) -> bool:
    code = normalize_feature_code(feature_code)
    return bool(db.scalar(select(CompanyFeature.enabled).where(
        CompanyFeature.company_id == company_id,
        CompanyFeature.feature_code == code,
    )))


def require_company_feature(db: Session, company_id: int, feature_code: str) -> None:
    if not is_feature_enabled(db, company_id, feature_code):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="feature_not_enabled")


def enabled_company_ids(db: Session, feature_code: str) -> list[int]:
    code = normalize_feature_code(feature_code)
    return list(db.scalars(select(CompanyFeature.company_id).where(
        CompanyFeature.feature_code == code,
        CompanyFeature.enabled.is_(True),
    )).all())


def enabled_features_for_user(db: Session, user: User) -> list[str]:
    stmt = select(CompanyFeature.feature_code).where(CompanyFeature.enabled.is_(True))
    if user.role != "admin":
        if user.company_id is None:
            return []
        stmt = stmt.where(CompanyFeature.company_id == user.company_id)
    return sorted(set(db.scalars(stmt).all()))


def list_company_features(db: Session, company_id: int) -> list[CompanyFeature]:
    stored = {
        item.feature_code: item
        for item in db.scalars(select(CompanyFeature).where(CompanyFeature.company_id == company_id)).all()
    }
    return [stored.get(code) or CompanyFeature(company_id=company_id, feature_code=code, enabled=False) for code in FEATURE_CATALOG]


def set_company_feature(
    db: Session,
    *,
    company_id: int,
    feature_code: str,
    enabled: bool,
    actor: User,
) -> CompanyFeature:
    code = normalize_feature_code(feature_code)
    setting = db.scalar(select(CompanyFeature).where(
        CompanyFeature.company_id == company_id,
        CompanyFeature.feature_code == code,
    ))
    if setting is None:
        setting = CompanyFeature(company_id=company_id, feature_code=code, enabled=False)
        db.add(setting)
    changed = setting.enabled != enabled
    setting.enabled = enabled
    setting.enabled_at = utc_now() if enabled else None
    setting.enabled_by_id = actor.id
    if changed:
        record_audit_event(
            db,
            action="company.feature_enabled" if enabled else "company.feature_disabled",
            summary=f"Modulo {code} {'habilitado' if enabled else 'deshabilitado'}",
            user=actor,
            company_id=company_id,
            resource_type="company_feature",
            resource_id=code,
            metadata={"company_id": company_id, "feature_code": code, "enabled": enabled},
        )
    return setting
