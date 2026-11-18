from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.modules.articles.models import Article, ArticleStatus


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
) -> tuple[list[Article], int]:
    filters: list[ColumnElement[bool]] = []
    if status is not None:
        filters.append(Article.status == status)

    total = db.scalar(select(func.count()).select_from(Article).where(*filters)) or 0
    articles = db.scalars(
        select(Article)
        .where(*filters)
        .order_by(Article.created_at.desc(), Article.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return list(articles), total


def list_published(db: Session, *, offset: int, limit: int) -> tuple[list[Article], int]:
    filters = [Article.status == ArticleStatus.PUBLISHED]
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
