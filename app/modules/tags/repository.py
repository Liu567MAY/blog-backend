from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.articles.models import Article, ArticleStatus, article_tags
from app.modules.tags.models import Tag


def get_by_id(db: Session, tag_id: int) -> Tag | None:
    return db.get(Tag, tag_id)


def get_by_name(db: Session, name: str) -> Tag | None:
    return db.scalar(select(Tag).where(func.lower(Tag.name) == name.lower()))


def get_by_slug(db: Session, slug: str) -> Tag | None:
    return db.scalar(select(Tag).where(Tag.slug == slug))


def get_by_ids(db: Session, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    return list(db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all())


def list_all(db: Session) -> list[Tag]:
    return list(db.scalars(select(Tag).order_by(Tag.created_at.desc(), Tag.id.desc())).all())


def count_articles(db: Session, tag_id: int) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(article_tags).where(article_tags.c.tag_id == tag_id)
        )
        or 0
    )


def list_public_with_counts(db: Session) -> list[tuple[Tag, int]]:
    counts = (
        select(
            article_tags.c.tag_id.label("tag_id"),
            func.count(article_tags.c.article_id).label("article_count"),
        )
        .join(Article, Article.id == article_tags.c.article_id)
        .where(Article.status == ArticleStatus.PUBLISHED)
        .group_by(article_tags.c.tag_id)
        .subquery()
    )
    rows = db.execute(
        select(Tag, counts.c.article_count)
        .join(counts, counts.c.tag_id == Tag.id)
        .order_by(Tag.created_at.desc(), Tag.id.desc())
    ).all()
    return [(row[0], row[1]) for row in rows]


def add(db: Session, tag: Tag) -> None:
    db.add(tag)


def delete(db: Session, tag: Tag) -> None:
    db.delete(tag)
