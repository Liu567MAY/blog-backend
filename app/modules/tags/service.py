from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.slug import normalize_manual_slug, slugify
from app.modules.tags import repository
from app.modules.tags.models import Tag
from app.modules.tags.schemas import TagCreateRequest, TagUpdateRequest


def _normalize_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValidationError("标签名称不能为空")
    return normalized


def _ensure_name_available(db: Session, name: str, *, exclude_id: int | None = None) -> None:
    existing = repository.get_by_name(db, name)
    if existing is not None and existing.id != exclude_id:
        raise ConflictError(f"标签名称已存在: {name}")


def _resolve_create_slug(db: Session, name: str, manual_slug: str | None) -> str:
    if manual_slug is not None:
        slug = normalize_manual_slug(manual_slug)
        if repository.get_by_slug(db, slug) is not None:
            raise ConflictError(f"slug 已存在: {slug}")
        return slug

    base = slugify(name, fallback_prefix="tag")
    slug = base
    suffix = 2
    while repository.get_by_slug(db, slug) is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def create_tag(db: Session, data: TagCreateRequest) -> Tag:
    name = _normalize_name(data.name)
    _ensure_name_available(db, name)
    slug = _resolve_create_slug(db, name, data.slug)
    tag = Tag(name=name, slug=slug)
    repository.add(db, tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("标签名称或 slug 已存在") from None
    db.refresh(tag)
    return tag


def list_tags(db: Session) -> list[Tag]:
    return repository.list_all(db)


def list_public_tags(db: Session) -> list[tuple[Tag, int]]:
    return repository.list_public_with_counts(db)


def get_tag(db: Session, tag_id: int) -> Tag:
    tag = repository.get_by_id(db, tag_id)
    if tag is None:
        raise NotFoundError("标签不存在")
    return tag


def get_tags_for_article(db: Session, tag_ids: list[int]) -> list[Tag]:
    """去重并校验文章提交的标签；任一不存在则整体拒绝。"""
    unique_ids = list(dict.fromkeys(tag_ids))
    if not unique_ids:
        return []
    tags = repository.get_by_ids(db, unique_ids)
    by_id = {tag.id: tag for tag in tags}
    missing = [tag_id for tag_id in unique_ids if tag_id not in by_id]
    if missing:
        formatted = ", ".join(str(tag_id) for tag_id in missing)
        raise ValidationError(f"标签不存在: {formatted}")
    return [by_id[tag_id] for tag_id in unique_ids]


def update_tag(db: Session, tag_id: int, data: TagUpdateRequest) -> Tag:
    tag = get_tag(db, tag_id)
    provided = data.model_fields_set
    if not provided:
        raise ValidationError("至少提供一个需要修改的字段")

    name = tag.name
    if "name" in provided:
        if data.name is None:
            raise ValidationError("标签名称不能为空")
        name = _normalize_name(data.name)
        _ensure_name_available(db, name, exclude_id=tag.id)

    slug = tag.slug
    if "slug" in provided:
        if data.slug is None:
            raise ValidationError("slug 不能为 null")
        slug = normalize_manual_slug(data.slug)
        existing = repository.get_by_slug(db, slug)
        if existing is not None and existing.id != tag.id:
            raise ConflictError(f"slug 已存在: {slug}")

    tag.name = name
    tag.slug = slug
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("标签名称或 slug 已存在") from None
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag_id: int) -> None:
    tag = get_tag(db, tag_id)
    if repository.count_articles(db, tag.id) > 0:
        raise ConflictError("标签仍被文章使用，无法删除")
    repository.delete(db, tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("标签仍被文章使用，无法删除") from None
