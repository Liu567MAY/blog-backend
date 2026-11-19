"""add article autosave snapshots

Revision ID: d8e4f1a2b6c9
Revises: c7d9e2f4a6b8
Create Date: 2026-11-18 18:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "d8e4f1a2b6c9"
down_revision: str | None = "c7d9e2f4a6b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "article_autosave",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.String(length=500), nullable=True),
        sa.Column(
            "content_markdown",
            sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_article_autosave_admin_user_id",
        "article_autosave",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_article_autosave_article_id",
        "article_autosave",
        ["article_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_article_autosave_admin_user_id_admin_user",
        "article_autosave",
        "admin_user",
        ["admin_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_article_autosave_article_id_article",
        "article_autosave",
        "article",
        ["article_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_article_autosave_article_id_article", "article_autosave", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_article_autosave_admin_user_id_admin_user",
        "article_autosave",
        type_="foreignkey",
    )
    op.drop_index("ix_article_autosave_article_id", table_name="article_autosave")
    op.drop_index("ix_article_autosave_admin_user_id", table_name="article_autosave")
    op.drop_table("article_autosave")
