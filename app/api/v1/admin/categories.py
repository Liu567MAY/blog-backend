from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.infrastructure.database.session import get_db
from app.modules.auth.models import AdminUser
from app.modules.categories import service
from app.modules.categories.schemas import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
)

router = APIRouter()


@router.get("", response_model=list[CategoryResponse], summary="管理端分类列表")
def list_categories(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> list[CategoryResponse]:
    return [CategoryResponse.model_validate(category) for category in service.list_categories(db)]


@router.post("", response_model=CategoryResponse, status_code=201, summary="创建分类")
def create_category(
    data: CategoryCreateRequest,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CategoryResponse:
    category = service.create_category(db, data)
    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryResponse, summary="修改分类")
def update_category(
    category_id: int,
    data: CategoryUpdateRequest,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> CategoryResponse:
    category = service.update_category(db, category_id, data)
    return CategoryResponse.model_validate(category)


@router.delete(
    "/{category_id}",
    status_code=204,
    response_class=Response,
    summary="删除分类",
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> Response:
    service.delete_category(db, category_id)
    return Response(status_code=204)
