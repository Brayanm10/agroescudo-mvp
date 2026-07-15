from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_company_access, require_role, scope_companies_query
from app.db.session import get_db
from app.models import Company, User
from app.schemas import CompanyCreate, CompanyOut

router = APIRouter(prefix="/companies", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[CompanyOut])
def list_companies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Company]:
    stmt = scope_companies_query(select(Company), current_user, db)
    return list(db.scalars(stmt.order_by(Company.name)).all())


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyCreate,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Company:
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    require_company_access(db, current_user, company.id)
    return company
