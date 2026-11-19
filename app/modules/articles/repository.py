from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.modules.articles.models import Article, ArticleStatus
from app.modules.categories.models import Category
from app.modules.tags.models import Tag


def _keyword_filter(keyword: str) -> ColumnElement[bool]:
    return or_(
        Article.title.contains(keyword, autoescape=True),
        Article.summary.contains(keyword, autoescape=True),
        Article.content_markdown.contains(keyword, autoescape=True),
    )


def get_by_slug(db: Session, slug: str) -> Article | None:
    return db.scalar(select(Article).where(Article.slug == slug))


def get_by_id(db: Session, article_id: int) -> Article | None:
    return db.get(Article, article_id)


def get_published_by_slug(db: Session, slug: str) -> Article | None:
    return db.scalar(
        select(Article).where(
            Article.slug == slug,
            Article.status == ArticleStatus.PUBLISHED,
        )
    )


def list_for_admin(
    db: Session,
    *,
    offset: int,
    limit: int,
    status: ArticleStatus | None = None,
    keyword: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
) -> tuple[list[Article], int]:
    filters: list[ColumnElement[bool]] = []
    if status is not None:
        filters.append(Article.status == status)
    if keyword:
        filters.append(_keyword_filter(keyword))
    if category_id is not None:
        filters.append(Article.category_id == category_id)
    if tag_id is not None:
        filters.append(Article.tags.any(Tag.id == tag_id))

    total = db.scalar(select(func.count()).select_from(Article).where(*filters)) or 0
    articles = db.scalars(
        select(Article)
        .where(*filters)
        .order_by(Article.created_at.desc(), Article.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(articles), total


def list_published(
    db: Session,
    *,
    offset: int,
    limit: int,
    keyword: str | None = None,
    category_slug: str | None = None,
    tag_slug: str | None = None,
) -> tuple[list[Article], int]:
    filters: list[ColumnElement[bool]] = [Article.status == ArticleStatus.PUBLISHED]
    if keyword:
        filters.append(_keyword_filter(keyword))
    if category_slug:
        filters.append(Article.category.has(Category.slug == category_slug))
    if tag_slug:
        filters.append(Article.tags.any(Tag.slug == tag_slug))

    total = db.scalar(select(func.count()).select_from(Article).where(*filters)) or 0
    articles = db.scalars(
        select(Article)
        .where(*filters)
        .order_by(Article.published_at.desc(), Article.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(articles), total


def add(db: Session, article: Article) -> None:
    db.add(article)
    db.flush()


def delete(db: Session, article: Article) -> None:
    db.delete(article)
