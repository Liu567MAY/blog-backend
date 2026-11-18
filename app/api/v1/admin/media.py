from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin
from app.core.config import Settings, get_settings
from app.modules.auth.models import AdminUser
from app.modules.media import service
from app.modules.media.schemas import MediaUploadRequest, MediaUploadSignature

router = APIRouter()


@router.post(
    "/upload-signature",
    response_model=MediaUploadSignature,
    summary="获取 OSS 图片直传签名",
)
def create_upload_signature(
    data: MediaUploadRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    _admin: AdminUser = Depends(get_current_admin),
) -> MediaUploadSignature:
    return service.create_upload_signature(data, settings)
