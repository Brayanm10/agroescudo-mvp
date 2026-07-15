from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import EducationArticle, EducationProgress, User, utc_now
from app.schemas import EducationArticleOut, EducationCompleteOut
from app.services.audit import record_audit_event

router = APIRouter()


@router.get("/education/articles", response_model=list[EducationArticleOut])
def list_articles(
    locale: str = "es",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EducationArticle]:
    stmt = (
        select(EducationArticle)
        .where(EducationArticle.is_published.is_(True), EducationArticle.locale == locale)
        .order_by(EducationArticle.category.asc(), EducationArticle.title.asc())
    )
    return list(db.scalars(stmt).all())


@router.get("/education/articles/{slug}", response_model=EducationArticleOut)
def get_article(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EducationArticle:
    article = db.scalar(select(EducationArticle).where(EducationArticle.slug == slug, EducationArticle.is_published.is_(True)))
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Articulo no encontrado.")
    return article


@router.post("/education/articles/{article_id}/complete", response_model=EducationCompleteOut)
def complete_article(
    article_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EducationCompleteOut:
    article = db.get(EducationArticle, article_id)
    if article is None or not article.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Articulo no encontrado.")
    progress = db.scalar(
        select(EducationProgress).where(
            EducationProgress.user_id == current_user.id,
            EducationProgress.article_id == article_id,
        )
    )
    if progress is None:
        progress = EducationProgress(user_id=current_user.id, article_id=article_id)
        db.add(progress)
    record_audit_event(db, action="education.complete", summary="Articulo completado", user=current_user, resource_type="education_article", resource_id=article_id)
    db.commit()
    return EducationCompleteOut(article_id=article_id, completed_at=progress.completed_at or utc_now())
