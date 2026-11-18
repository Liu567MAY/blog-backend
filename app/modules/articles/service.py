import hashlib
import re
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationError
from app.modules.articles import repository
from app.modules.articles.models import Article, ArticleStatus
from app.modules.articles.schemas import ArticleCreateRequest

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_SLUG_LENGTH = 200


def _slugify_title(title: str) -> str:
    """提取标题中的 ASCII 字母数字生成 slug；中文等非 ASCII 字符会被过滤。"""
    ascii_part = title.lower().encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_part).strip("-")
    return slug[:_MAX_SLUG_LENGTH].rstrip("-")


def _generate_unique_slug(db: Session, title: str) -> str:
    base = _slugify_title(title)
    if not base:
        # 纯中文等无法转写的标题：用标题哈希兜底，保证稳定且非空
        digest = hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]
        base = f"post-{digest}"
    slug = base
    suffix = 2
    while repository.get_by_slug(db, slug) is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def _resolve_slug(db: Session, title: str, manual_slug: str | None) -> str:
    if manual_slug is None:
        return _generate_unique_slug(db, title)
    slug = manual_slug.strip().lower()
    if not _SLUG_PATTERN.match(slug) or len(slug) > _MAX_SLUG_LENGTH:
        raise ValidationError("slug 只能包含小写字母、数字和连字符，且不能以连字符开头或结尾")
    if repository.get_by_slug(db, slug) is not None:
        raise ConflictError(f"slug 已存在: {slug}")
    return slug


def create_article(db: Session, data: ArticleCreateRequest) -> Article:
    """新增文章，事务由本层统一控制。"""
    title = data.title.strip()
    if not title:
        raise ValidationError("标题不能为空")
    if data.status is ArticleStatus.PUBLISHED and not data.content_markdown.strip():
        raise ValidationError("发布文章必须包含非空正文")

    slug = _resolve_slug(db, title, data.slug)
    now = datetime.now(timezone.utc)
    article = Article(
        title=title,
        slug=slug,
        summary=data.summary,
        content_markdown=data.content_markdown,
        status=data.status,
        published_at=now if data.status is ArticleStatus.PUBLISHED else None,
    )
    repository.add(db, article)
    try:
        db.commit()
    except IntegrityError:
        # 并发场景下唯一约束兜底
        db.rollback()
        raise ConflictError(f"slug 已存在: {slug}") from None
    db.refresh(article)
    return article
