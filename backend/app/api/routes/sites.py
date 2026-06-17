from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, require_site_access, scope_company_query
from app.db.session import get_db
from app.models import Company, Site, User
from app.schemas import SiteCreate, SiteOut

router = APIRouter(prefix="/sites", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[SiteOut])
def list_sites(
    company_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Site]:
    if company_id is not None and not (current_user.role in {"admin", "technician"} or current_user.company_id == company_id):
        return []
    stmt = scope_company_query(select(Site), Site, current_user)
    if company_id is not None:
        stmt = stmt.where(Site.company_id == company_id)
    return list(db.scalars(stmt.order_by(Site.name)).all())


@router.post("", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def create_site(
    payload: SiteCreate,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Site:
    if db.get(Company, payload.company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    site = Site(company_id=payload.company_id, name=payload.name, location=payload.location)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.get("/{site_id}", response_model=SiteOut)
def get_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Site:
    return require_site_access(db, current_user, site_id)
