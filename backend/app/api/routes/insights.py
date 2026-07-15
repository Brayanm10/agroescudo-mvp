from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_storage_unit_access, scope_storage_units_query
from app.db.session import get_db
from app.models import StorageUnit, User
from app.schemas import InsightsOut, StorageUnitInsightOut
from app.services.insights import build_storage_unit_insight

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/insights", response_model=InsightsOut)
def list_insights(
    period: Literal["24h", "7d", "30d"] = Query(default="7d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InsightsOut:
    units = list(db.scalars(scope_storage_units_query(select(StorageUnit), current_user, db).order_by(StorageUnit.name)).all())
    return InsightsOut(period=period, insights=[build_storage_unit_insight(db, unit, period) for unit in units])


@router.get("/storage-units/{storage_unit_id}/insights", response_model=StorageUnitInsightOut)
def get_storage_unit_insight(
    storage_unit_id: int,
    period: Literal["24h", "7d", "30d"] = Query(default="7d"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StorageUnitInsightOut:
    unit = require_storage_unit_access(db, current_user, storage_unit_id)
    return build_storage_unit_insight(db, unit, period)
