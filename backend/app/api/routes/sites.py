from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, require_site_access, scope_sites_query
from app.db.session import get_db
from app.models import Company, Site, User
from app.schemas import SiteCreate, SiteOut, SiteUpdate
from app.services.audit import record_audit_event

router = APIRouter(prefix="/sites", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[SiteOut])
def list_sites(
    company_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Site]:
    stmt = scope_sites_query(select(Site), current_user, db)
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
    site = Site(
        **payload.model_dump(),
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


@router.patch("/{site_id}", response_model=SiteOut)
def update_site(
    site_id: int,
    payload: SiteUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    values = payload.model_dump(exclude_unset=True)
    boundary_changed = "boundary_geojson" in values and values["boundary_geojson"] != site.boundary_geojson
    for key, value in values.items():
        setattr(site, key, value)
    if boundary_changed:
        record_audit_event(
            db,
            action="pluviometry.site_boundary_updated",
            summary=f"Limite geografico actualizado para el predio {site.name}.",
            user=current_user,
            company_id=site.company_id,
            resource_type="site",
            resource_id=site.id,
        )
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
