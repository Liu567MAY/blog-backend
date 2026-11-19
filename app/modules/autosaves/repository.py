from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.articles.models import Article
from app.modules.autosaves.models import ArticleAutosave


def get_by_id(db: Session, autosave_id: str) -> ArticleAutosave | None:
    return db.get(ArticleAutosave, autosave_id)


def get_owned(
    db: Session,
    autosave_id: str,
    admin_user_id: int,
    *,
    for_update: bool = False,
) -> ArticleAutosave | None:
    statement = select(ArticleAutosave).where(
        ArticleAutosave.id == autosave_id,
        ArticleAutosave.admin_user_id == admin_user_id,
    )
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def list_owned(
    db: Session,
    admin_user_id: int,
    *,
    article_id: int | None = None,
) -> list[ArticleAutosave]:
    statement = select(ArticleAutosave).where(ArticleAutosave.admin_user_id == admin_user_id)
    if article_id is not None:
        statement = statement.where(ArticleAutosave.article_id == article_id)
    statement = statement.order_by(ArticleAutosave.updated_at.desc(), ArticleAutosave.id.desc())
    return list(db.scalars(statement).all())


def article_exists(db: Session, article_id: int) -> bool:
    return db.get(Article, article_id) is not None


def add(db: Session, autosave: ArticleAutosave) -> None:
    db.add(autosave)


def delete(db: Session, autosave: ArticleAutosave) -> None:
    db.delete(autosave)


def delete_by_article_id(db: Session, article_id: int) -> None:
    db.execute(sa_delete(ArticleAutosave).where(ArticleAutosave.article_id == article_id))
