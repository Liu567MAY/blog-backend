from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.infrastructure.database.session import get_db
from app.modules.auth.models import AdminUser
from app.modules.tags import service
from app.modules.tags.schemas import TagCreateRequest, TagResponse, TagUpdateRequest

router = APIRouter()


@router.get("", response_model=list[TagResponse], summary="管理端标签列表")
def list_tags(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> list[TagResponse]:
    return [TagResponse.model_validate(tag) for tag in service.list_tags(db)]


@router.post("", response_model=TagResponse, status_code=201, summary="创建标签")
def create_tag(
    data: TagCreateRequest,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> TagResponse:
    tag = service.create_tag(db, data)
    return TagResponse.model_validate(tag)


@router.patch("/{tag_id}", response_model=TagResponse, summary="修改标签")
def update_tag(
    tag_id: int,
    data: TagUpdateRequest,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> TagResponse:
    tag = service.update_tag(db, tag_id, data)
    return TagResponse.model_validate(tag)


@router.delete("/{tag_id}", status_code=204, response_class=Response, summary="删除标签")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> Response:
    service.delete_tag(db, tag_id)
    return Response(status_code=204)
