from typing import Protocol

import oss2

from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError


class OssUploadSigner(Protocol):
    def sign_url(
        self,
        method: str,
        key: str,
        expires: int,
        headers: dict[str, str] | None = None,
        **kwargs: object,
    ) -> str: ...


# (Settings 字段, 环境变量名)
_REQUIRED_CONFIG = (
    ("oss_bucket", "OSS_BUCKET"),
    ("oss_endpoint", "OSS_ENDPOINT"),
    ("oss_region", "OSS_REGION"),
    ("oss_access_key_id", "OSS_ACCESS_KEY_ID"),
    ("oss_access_key_secret", "OSS_ACCESS_KEY_SECRET"),
    ("oss_public_base_url", "OSS_PUBLIC_BASE_URL"),
)


def _missing_config(settings: Settings) -> list[str]:
    return [
        env_name for field_name, env_name in _REQUIRED_CONFIG if not getattr(settings, field_name)
    ]


def build_oss_client(settings: Settings) -> OssUploadSigner:
    """按配置创建 OSS 客户端；配置不完整时明确拒绝，不生成假签名。"""
    missing = _missing_config(settings)
    if missing:
        raise ServiceUnavailableError(f"OSS 配置不完整，缺少: {', '.join(missing)}")

    endpoint = settings.oss_endpoint or ""
    if not endpoint.startswith(("https://", "http://")):
        raise ServiceUnavailableError("OSS_ENDPOINT 必须以 http:// 或 https:// 开头")

    public_base_url = settings.oss_public_base_url or ""
    if not public_base_url.startswith(("https://", "http://")):
        raise ServiceUnavailableError("OSS_PUBLIC_BASE_URL 必须以 http:// 或 https:// 开头")

    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    return oss2.Bucket(
        auth,
        endpoint,
        settings.oss_bucket,
        region=settings.oss_region,
    )
