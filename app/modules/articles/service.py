import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.articles import repository
from app.modules.articles.models import Article, ArticleStatus
from app.modules.articles.schemas import ArticleCreateRequest, ArticleUpdateRequest

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MAX_SLUG_LENGTH = 200

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class ArticlePage:
    items: list[Article]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size


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


def _normalize_manual_slug(slug: str) -> str:
    normalized = slug.strip().lower()
    if not _SLUG_PATTERN.match(normalized) or len(normalized) > _MAX_SLUG_LENGTH:
        raise ValidationError("slug 只能包含小写字母、数字和连字符，且不能以连字符开头或结尾")
    return normalized


def _resolve_slug(db: Session, title: str, manual_slug: str | None) -> str:
    if manual_slug is None:
        return _generate_unique_slug(db, title)
    slug = _normalize_manual_slug(manual_slug)
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


def list_admin_articles(
    db: Session,
    *,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
    status: ArticleStatus | None = None,
) -> ArticlePage:
    """管理端列表：包含草稿和已发布文章，按创建时间倒序。"""
    offset = (page - 1) * page_size
    items, total = repository.list_for_admin(db, offset=offset, limit=page_size, status=status)
    return ArticlePage(items=items, total=total, page=page, page_size=page_size)


def get_admin_article(db: Session, article_id: int) -> Article:
    """管理端详情：可查看任意状态的文章，包含 Markdown 原文。"""
    article = repository.get_by_id(db, article_id)
    if article is None:
        raise NotFoundError("文章不存在")
    return article


def list_public_articles(
    db: Session,
    *,
    page: int = DEFAULT_PAGE,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> ArticlePage:
    """公开端列表：仅返回已发布文章，按发布时间倒序。"""
    offset = (page - 1) * page_size
    items, total = repository.list_published(db, offset=offset, limit=page_size)
    return ArticlePage(items=items, total=total, page=page, page_size=page_size)


def get_public_article(db: Session, slug: str) -> Article:
    """公开端详情：草稿与不存在的文章统一视为不存在。"""
    article = repository.get_published_by_slug(db, slug)
    if article is None:
        raise NotFoundError("文章不存在")
    return article


def update_article(db: Session, article_id: int, data: ArticleUpdateRequest) -> Article:
    """部分更新文章，事务由本层统一控制。"""
    article = repository.get_by_id(db, article_id)
    if article is None:
        raise NotFoundError("文章不存在")

    provided = data.model_fields_set
    if not provided:
        raise ValidationError("至少提供一个需要修改的字段")

    title = article.title
    if "title" in provided:
        if data.title is None:
            raise ValidationError("标题不能为空")
        title = data.title.strip()
        if not title:
            raise ValidationError("标题不能为空")

    content_markdown = article.content_markdown
    if "content_markdown" in provided:
        if data.content_markdown is None:
            raise ValidationError("正文不能为 null")
        content_markdown = data.content_markdown

    status = article.status
    if "status" in provided:
        if data.status is None:
            raise ValidationError("状态不能为 null")
        status = data.status
    if status is ArticleStatus.PUBLISHED and not content_markdown.strip():
        raise ValidationError("发布文章必须包含非空正文")

    slug = article.slug
    if "slug" in provided:
        if data.slug is None:
            raise ValidationError("slug 不能为 null")
        slug = _normalize_manual_slug(data.slug)
        existing = repository.get_by_slug(db, slug)
        if existing is not None and existing.id != article.id:
            raise ConflictError(f"slug 已存在: {slug}")

    summary = article.summary
    if "summary" in provided:
        summary = data.summary

    now = datetime.now(timezone.utc)
    was_published = article.status is ArticleStatus.PUBLISHED
    article.title = title
    article.slug = slug
    article.summary = summary
    article.content_markdown = content_markdown
    article.status = status
    if status is ArticleStatus.PUBLISHED:
        if not was_published or article.published_at is None:
            article.published_at = now
    else:
        article.published_at = None
    article.updated_at = now

    try:
        db.commit()
    except IntegrityError:
        # 并发更新为同一 slug 时由唯一约束兜底
        db.rollback()
        raise ConflictError(f"slug 已存在: {slug}") from None
    db.refresh(article)
    return article


def delete_article(db: Session, article_id: int) -> None:
    """物理删除文章，事务由本层统一控制。"""
    article = repository.get_by_id(db, article_id)
    if article is None:
        raise NotFoundError("文章不存在")
    repository.delete(db, article)
    db.commit()
