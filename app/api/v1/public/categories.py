from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.modules.categories import service
from app.modules.categories.models import Category
from app.modules.categories.schemas import CategoryPublicResponse, CategoryResponse

router = APIRouter()


def _to_public(category: Category, article_count: int) -> CategoryPublicResponse:
    base = CategoryResponse.model_validate(category).model_dump()
    return CategoryPublicResponse(**base, article_count=article_count)


@router.get("", response_model=list[CategoryPublicResponse], summary="公开分类列表")
def list_categories(db: Session = Depends(get_db)) -> list[CategoryPublicResponse]:
    return [
        _to_public(category, article_count)
        for category, article_count in service.list_public_categories(db)
    ]
