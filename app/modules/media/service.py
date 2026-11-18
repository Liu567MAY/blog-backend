from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.modules.media.oss import build_oss_client
from app.modules.media.schemas import (
    MediaContentType,
    MediaUploadRequest,
    MediaUploadSignature,
)

_CONTENT_TYPE_EXTENSIONS: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}


def _object_key(prefix: str, content_type: MediaContentType) -> str:
    # 不信任原始文件名：用 UUID 作为文件名，避免路径穿越、重名和非 ASCII 问题
    safe_prefix = prefix.strip("/") or "articles"
    extension = _CONTENT_TYPE_EXTENSIONS[content_type]
    date_path = datetime.now(timezone.utc).strftime("%Y/%m")
    return f"{safe_prefix}/{date_path}/{uuid4().hex}.{extension}"


def create_upload_signature(data: MediaUploadRequest, settings: Settings) -> MediaUploadSignature:
    max_size = settings.oss_max_image_size_bytes
    if data.size > max_size:
        raise ValidationError(f"图片大小不能超过 {max_size // (1024 * 1024)}MB")

    # 先完成请求校验，再检查 OSS 配置并发起签名
    client = build_oss_client(settings)
    object_key = _object_key(settings.oss_upload_prefix, data.content_type)
    headers = {"Content-Type": data.content_type}
    upload_url = client.sign_url(
        "PUT",
        object_key,
        settings.oss_upload_expire_seconds,
        headers=headers,
    )
    public_url = f"{(settings.oss_public_base_url or '').rstrip('/')}/{object_key}"

    return MediaUploadSignature(
        upload_url=upload_url,
        method="PUT",
        headers=headers,
        object_key=object_key,
        public_url=public_url,
        expires_in=settings.oss_upload_expire_seconds,
    )
