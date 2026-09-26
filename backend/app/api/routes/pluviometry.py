from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import PluviometryMapSnapshotOut, PluviometrySiteOut
from app.services.pluviometry import build_pluviometry_map_snapshot, list_pluviometry_sites
from app.services.company_features import PLUVIOMETRY, require_company_feature


router = APIRouter(prefix="/pluviometry", dependencies=[Depends(get_current_user)])


@router.get("/sites", response_model=list[PluviometrySiteOut])
def list_sites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PluviometrySiteOut]:
    if current_user.role != "admin":
        if current_user.company_id is None:
            require_company_feature(db, -1, PLUVIOMETRY)
        require_company_feature(db, current_user.company_id, PLUVIOMETRY)
    return list_pluviometry_sites(db, current_user)


@router.get("/sites/{site_id}/map", response_model=PluviometryMapSnapshotOut)
def get_site_map(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PluviometryMapSnapshotOut:
    return build_pluviometry_map_snapshot(db, current_user, site_id)
