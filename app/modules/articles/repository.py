from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.articles.models import Article


def get_by_slug(db: Session, slug: str) -> Article | None:
    return db.scalar(select(Article).where(Article.slug == slug))


def add(db: Session, article: Article) -> None:
    db.add(article)
    db.flush()
