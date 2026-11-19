from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.slug import normalize_manual_slug, slugify
from app.modules.categories import repository
from app.modules.categories.models import Category
from app.modules.categories.schemas import CategoryCreateRequest, CategoryUpdateRequest


def _normalize_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValidationError("分类名称不能为空")
    return normalized


def _ensure_name_available(db: Session, name: str, *, exclude_id: int | None = None) -> None:
    existing = repository.get_by_name(db, name)
    if existing is not None and existing.id != exclude_id:
        raise ConflictError(f"分类名称已存在: {name}")


def _resolve_create_slug(db: Session, name: str, manual_slug: str | None) -> str:
    if manual_slug is not None:
        slug = normalize_manual_slug(manual_slug)
        if repository.get_by_slug(db, slug) is not None:
            raise ConflictError(f"slug 已存在: {slug}")
        return slug

    base = slugify(name, fallback_prefix="category")
    slug = base
    suffix = 2
    while repository.get_by_slug(db, slug) is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def create_category(db: Session, data: CategoryCreateRequest) -> Category:
    name = _normalize_name(data.name)
    _ensure_name_available(db, name)
    slug = _resolve_create_slug(db, name, data.slug)
    category = Category(name=name, slug=slug, description=data.description)
    repository.add(db, category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("分类名称或 slug 已存在") from None
    db.refresh(category)
    return category


def list_categories(db: Session) -> list[Category]:
    return repository.list_all(db)


def list_public_categories(db: Session) -> list[tuple[Category, int]]:
    return repository.list_public_with_counts(db)


def get_category(db: Session, category_id: int) -> Category:
    category = repository.get_by_id(db, category_id)
    if category is None:
        raise NotFoundError("分类不存在")
    return category


def get_category_for_article(db: Session, category_id: int) -> Category:
    """校验文章提交的分类；不存在属于请求参数错误而非 404。"""
    category = repository.get_by_id(db, category_id)
    if category is None:
        raise ValidationError("分类不存在")
    return category


def update_category(db: Session, category_id: int, data: CategoryUpdateRequest) -> Category:
    category = get_category(db, category_id)
    provided = data.model_fields_set
    if not provided:
        raise ValidationError("至少提供一个需要修改的字段")

    name = category.name
    if "name" in provided:
        if data.name is None:
            raise ValidationError("分类名称不能为空")
        name = _normalize_name(data.name)
        _ensure_name_available(db, name, exclude_id=category.id)

    slug = category.slug
    if "slug" in provided:
        if data.slug is None:
            raise ValidationError("slug 不能为 null")
        slug = normalize_manual_slug(data.slug)
        existing = repository.get_by_slug(db, slug)
        if existing is not None and existing.id != category.id:
            raise ConflictError(f"slug 已存在: {slug}")

    description = category.description
    if "description" in provided:
        description = data.description

    category.name = name
    category.slug = slug
    category.description = description
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("分类名称或 slug 已存在") from None
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = get_category(db, category_id)
    if repository.count_articles(db, category.id) > 0:
        raise ConflictError("分类下仍有文章，无法删除")
    repository.delete(db, category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("分类下仍有文章，无法删除") from None
