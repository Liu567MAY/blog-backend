from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.modules.tags import service
from app.modules.tags.models import Tag
from app.modules.tags.schemas import TagPublicResponse, TagResponse

router = APIRouter()


def _to_public(tag: Tag, article_count: int) -> TagPublicResponse:
    base = TagResponse.model_validate(tag).model_dump()
    return TagPublicResponse(**base, article_count=article_count)


@router.get("", response_model=list[TagPublicResponse], summary="公开标签列表")
def list_tags(db: Session = Depends(get_db)) -> list[TagPublicResponse]:
    return [_to_public(tag, article_count) for tag, article_count in service.list_public_tags(db)]
