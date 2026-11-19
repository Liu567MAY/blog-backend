from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.autosaves import repository
from app.modules.autosaves.models import ArticleAutosave
from app.modules.autosaves.schemas import AutosavePutRequest


def _validate_article(db: Session, article_id: int | None) -> None:
    if article_id is not None and not repository.article_exists(db, article_id):
        raise ValidationError("文章不存在")


def _apply_content(snapshot: ArticleAutosave, data: AutosavePutRequest) -> None:
    snapshot.title = data.title
    snapshot.slug = data.slug
    snapshot.summary = data.summary
    snapshot.content_markdown = data.content_markdown
    snapshot.article_id = data.article_id


def put_autosave(
    db: Session,
    autosave_id: UUID,
    admin_user_id: int,
    data: AutosavePutRequest,
) -> ArticleAutosave:
    """按 UUID upsert 快照；revision 是客户端期望的当前版本。"""
    key = str(autosave_id)
    snapshot = repository.get_owned(db, key, admin_user_id, for_update=True)

    if snapshot is None:
        if repository.get_by_id(db, key) is not None:
            # 其他管理员的快照：不泄露存在性，也不允许覆盖
            db.rollback()
            raise NotFoundError("自动保存快照不存在")
        if data.revision != 0:
            db.rollback()
            raise ConflictError("自动保存版本冲突，请刷新后重试")
        _validate_article(db, data.article_id)
        now = datetime.now(timezone.utc)
        snapshot = ArticleAutosave(
            id=key,
            admin_user_id=admin_user_id,
            article_id=data.article_id,
            title=data.title,
            slug=data.slug,
            summary=data.summary,
            content_markdown=data.content_markdown,
            created_at=now,
            updated_at=now,
            revision=1,
        )
        repository.add(db, snapshot)
    else:
        if data.revision != snapshot.revision:
            db.rollback()
            raise ConflictError("自动保存版本冲突，请刷新后重试")
        _validate_article(db, data.article_id)
        _apply_content(snapshot, data)
        snapshot.updated_at = datetime.now(timezone.utc)
        snapshot.revision += 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("自动保存失败，请重试") from None
    db.refresh(snapshot)
    return snapshot


def get_autosave(db: Session, autosave_id: UUID, admin_user_id: int) -> ArticleAutosave:
    snapshot = repository.get_owned(db, str(autosave_id), admin_user_id)
    if snapshot is None:
        raise NotFoundError("自动保存快照不存在")
    return snapshot


def list_autosaves(
    db: Session,
    admin_user_id: int,
    *,
    article_id: int | None = None,
) -> list[ArticleAutosave]:
    return repository.list_owned(db, admin_user_id, article_id=article_id)


def delete_autosave(db: Session, autosave_id: UUID, admin_user_id: int) -> None:
    snapshot = repository.get_owned(db, str(autosave_id), admin_user_id)
    if snapshot is None:
        raise NotFoundError("自动保存快照不存在")
    repository.delete(db, snapshot)
    db.commit()


def cleanup_for_article_write(
    db: Session,
    autosave_id: UUID | None,
    admin_user_id: int | None,
) -> None:
    """正式文章保存事务内清理本人快照；不存在或不属于本人时忽略。"""
    if autosave_id is None or admin_user_id is None:
        return
    snapshot = repository.get_owned(db, str(autosave_id), admin_user_id)
    if snapshot is not None:
        repository.delete(db, snapshot)


def delete_for_article(db: Session, article_id: int) -> None:
    """文章删除事务内清理关联快照。"""
    repository.delete_by_article_id(db, article_id)
