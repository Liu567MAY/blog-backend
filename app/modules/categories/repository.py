from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.articles.models import Article, ArticleStatus
from app.modules.categories.models import Category


def get_by_id(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def get_by_name(db: Session, name: str) -> Category | None:
    return db.scalar(select(Category).where(func.lower(Category.name) == name.lower()))


def get_by_slug(db: Session, slug: str) -> Category | None:
    return db.scalar(select(Category).where(Category.slug == slug))


def list_all(db: Session) -> list[Category]:
    return list(
        db.scalars(select(Category).order_by(Category.created_at.desc(), Category.id.desc())).all()
    )


def count_articles(db: Session, category_id: int) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(Article).where(Article.category_id == category_id)
        )
        or 0
    )


def list_public_with_counts(db: Session) -> list[tuple[Category, int]]:
    counts = (
        select(
            Article.category_id.label("category_id"),
            func.count(Article.id).label("article_count"),
        )
        .where(
            Article.category_id.is_not(None),
            Article.status == ArticleStatus.PUBLISHED,
        )
        .group_by(Article.category_id)
        .subquery()
    )
    rows = db.execute(
        select(Category, counts.c.article_count)
        .join(counts, counts.c.category_id == Category.id)
        .order_by(Category.created_at.desc(), Category.id.desc())
    ).all()
    return [(row[0], row[1]) for row in rows]


def add(db: Session, category: Category) -> None:
    db.add(category)


def delete(db: Session, category: Category) -> None:
    db.delete(category)
