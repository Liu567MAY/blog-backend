from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.infrastructure.database.session import get_db
from app.modules.auth.models import AdminUser
from app.modules.autosaves import service
from app.modules.autosaves.schemas import (
    AutosaveListItem,
    AutosavePutRequest,
    AutosaveResponse,
)

router = APIRouter()


@router.get("", response_model=list[AutosaveListItem], summary="可恢复的自动保存列表")
def list_autosaves(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    article_id: Annotated[int | None, Query(ge=1)] = None,
) -> list[AutosaveListItem]:
    snapshots = service.list_autosaves(db, admin.id, article_id=article_id)
    return [AutosaveListItem.model_validate(snapshot) for snapshot in snapshots]


@router.put("/{autosave_id}", response_model=AutosaveResponse, summary="自动保存快照")
def put_autosave(
    autosave_id: UUID,
    data: AutosavePutRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> AutosaveResponse:
    snapshot = service.put_autosave(db, autosave_id, admin.id, data)
    return AutosaveResponse.model_validate(snapshot)


@router.get("/{autosave_id}", response_model=AutosaveResponse, summary="自动保存快照详情")
def get_autosave(
    autosave_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> AutosaveResponse:
    snapshot = service.get_autosave(db, autosave_id, admin.id)
    return AutosaveResponse.model_validate(snapshot)


@router.delete(
    "/{autosave_id}",
    status_code=204,
    response_class=Response,
    summary="删除自动保存快照",
)
def delete_autosave(
    autosave_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> Response:
    service.delete_autosave(db, autosave_id, admin.id)
    return Response(status_code=204)
