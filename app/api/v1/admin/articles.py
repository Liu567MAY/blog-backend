from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.infrastructure.database.session import get_db
from app.modules.articles import service
from app.modules.articles.models import ArticleStatus
from app.modules.articles.schemas import (
    AdminArticleDetail,
    AdminArticleListItem,
    AdminArticleListResponse,
    ArticleCreateRequest,
    ArticleResponse,
    ArticleUpdateRequest,
)
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


@router.get("", response_model=AdminArticleListResponse, summary="管理端文章列表")
def list_articles(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
    page: Annotated[int, Query(ge=1)] = service.DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, le=service.MAX_PAGE_SIZE)] = service.DEFAULT_PAGE_SIZE,
    status: Annotated[ArticleStatus | None, Query()] = None,
) -> AdminArticleListResponse:
    result = service.list_admin_articles(db, page=page, page_size=page_size, status=status)
    return AdminArticleListResponse(
        items=[AdminArticleListItem.model_validate(article) for article in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get("/{article_id}", response_model=AdminArticleDetail, summary="管理端文章详情")
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> AdminArticleDetail:
    article = service.get_admin_article(db, article_id)
    return AdminArticleDetail.model_validate(article)


@router.patch("/{article_id}", response_model=AdminArticleDetail, summary="修改文章")
def update_article(
    article_id: int,
    data: ArticleUpdateRequest,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> AdminArticleDetail:
    article = service.update_article(db, article_id, data)
    return AdminArticleDetail.model_validate(article)


@router.delete(
    "/{article_id}",
    status_code=204,
    response_class=Response,
    summary="删除文章",
)
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> Response:
    service.delete_article(db, article_id)
    return Response(status_code=204)
