from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Table, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.modules.categories.models import Category
    from app.modules.tags.models import Tag


class ArticleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


article_tags = Table(
    "article_tags",
    Base.metadata,
    Column("article_id", ForeignKey("article.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="RESTRICT"), primary_key=True),
    Index("ix_article_tags_tag_id", "tag_id"),
)


class Article(Base):
    __tablename__ = "article"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 只存 Markdown 原文，不生成 / 存储 HTML
    content_markdown: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False, default=""
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("category.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    status: Mapped[ArticleStatus] = mapped_column(
        SAEnum(ArticleStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ArticleStatus.DRAFT,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    category: Mapped["Category | None"] = relationship(back_populates="articles", lazy="joined")
    tags: Mapped[list["Tag"]] = relationship(
        secondary="article_tags",
        back_populates="articles",
        lazy="selectin",
        order_by="Tag.id",
    )
