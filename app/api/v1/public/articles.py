from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.infrastructure.database.session import get_db
from app.modules.articles import service
from app.modules.articles.schemas import (
    PublicArticleDetail,
    PublicArticleListItem,
    PublicArticleListResponse,
)

router = APIRouter()


@router.get("", response_model=PublicArticleListResponse, summary="公开文章列表")
def list_articles(
    db: Session = Depends(get_db),
    page: Annotated[int, Query(ge=1)] = service.DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, le=service.MAX_PAGE_SIZE)] = service.DEFAULT_PAGE_SIZE,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(max_length=200)] = None,
    tag: Annotated[str | None, Query(max_length=200)] = None,
) -> PublicArticleListResponse:
    result = service.list_public_articles(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        category=category,
        tag=tag,
    )
    return PublicArticleListResponse(
        items=[PublicArticleListItem.model_validate(article) for article in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get("/{slug}", response_model=PublicArticleDetail, summary="公开文章详情")
def get_article(slug: str, db: Session = Depends(get_db)) -> PublicArticleDetail:
    article = service.get_public_article(db, slug)
    return PublicArticleDetail.model_validate(article)
