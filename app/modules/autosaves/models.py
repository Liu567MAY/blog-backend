from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArticleAutosave(Base):
    __tablename__ = "article_autosave"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(
        ForeignKey("admin_user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    article_id: Mapped[int | None] = mapped_column(
        ForeignKey("article.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    slug: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_markdown: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False, default=""
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
