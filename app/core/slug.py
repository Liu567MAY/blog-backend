import hashlib
import re

from app.core.exceptions import ValidationError

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_SLUG_LENGTH = 200


def slugify(value: str, *, fallback_prefix: str) -> str:
    """生成 URL 安全 slug；纯中文等无法转写的值使用稳定哈希兜底。"""
    ascii_part = value.lower().encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_part).strip("-")
    if slug:
        return slug[:_MAX_SLUG_LENGTH].rstrip("-")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{fallback_prefix}-{digest}"


def normalize_manual_slug(slug: str) -> str:
    normalized = slug.strip().lower()
    if not _SLUG_PATTERN.match(normalized) or len(normalized) > _MAX_SLUG_LENGTH:
        raise ValidationError("slug 只能包含小写字母、数字和连字符，且不能以连字符开头或结尾")
    return normalized
