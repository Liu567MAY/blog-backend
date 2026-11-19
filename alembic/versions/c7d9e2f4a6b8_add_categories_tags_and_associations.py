"""add categories tags and article associations

Revision ID: c7d9e2f4a6b8
Revises: 89ad21ed6621
Create Date: 2026-11-18 18:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7d9e2f4a6b8"
down_revision: str | None = "89ad21ed6621"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "category",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    op.add_column("article", sa.Column("category_id", sa.Integer(), nullable=True))
    op.create_index("ix_article_category_id", "article", ["category_id"], unique=False)
    op.create_foreign_key(
        "fk_article_category_id_category",
        "article",
        "category",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "article_tags",
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("article_id", "tag_id"),
    )
    op.create_index("ix_article_tags_tag_id", "article_tags", ["tag_id"], unique=False)
    op.create_foreign_key(
        "fk_article_tags_article_id",
        "article_tags",
        "article",
        ["article_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_article_tags_tag_id",
        "article_tags",
        "tag",
        ["tag_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_article_tags_tag_id", "article_tags", type_="foreignkey")
    op.drop_constraint("fk_article_tags_article_id", "article_tags", type_="foreignkey")
    op.drop_index("ix_article_tags_tag_id", table_name="article_tags")
    op.drop_table("article_tags")

    op.drop_constraint("fk_article_category_id_category", "article", type_="foreignkey")
    op.drop_index("ix_article_category_id", table_name="article")
    op.drop_column("article", "category_id")

    op.drop_table("tag")
    op.drop_table("category")
