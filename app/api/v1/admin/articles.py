from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.infrastructure.database.session import get_db
from app.modules.articles import service
from app.modules.articles.schemas import ArticleCreateRequest, ArticleResponse
from app.modules.auth.models import AdminUser

router = APIRouter()


@router.post("", response_model=ArticleResponse, status_code=201, summary="新增文章")
def create_article(
    data: ArticleCreateRequest,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> ArticleResponse:
    article = service.create_article(db, data)
    return ArticleResponse.model_validate(article)
