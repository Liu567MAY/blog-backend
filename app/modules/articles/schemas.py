from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.articles.models import ArticleStatus
from app.modules.categories.schemas import CategoryBrief
from app.modules.tags.schemas import TagBrief


class ArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    content_markdown: str = ""
    status: ArticleStatus = ArticleStatus.DRAFT
    category_id: Annotated[int, Field(ge=1)] | None = None
    tag_ids: list[Annotated[int, Field(ge=1)]] | None = None
    autosave_id: UUID | None = None


class ArticleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    content_markdown: str | None = None
    status: ArticleStatus | None = None
    category_id: Annotated[int, Field(ge=1)] | None = None
    tag_ids: list[Annotated[int, Field(ge=1)]] | None = None
    autosave_id: UUID | None = None


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    summary: str | None
    status: ArticleStatus
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


# 管理端列表项与创建响应字段一致，直接复用
AdminArticleListItem = ArticleResponse


class AdminArticleDetail(AdminArticleListItem):
    content_markdown: str
    category: CategoryBrief | None
    tags: list[TagBrief]


class PublicArticleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    summary: str | None
    published_at: datetime | None


class PublicArticleDetail(PublicArticleListItem):
    content_markdown: str
    created_at: datetime
    updated_at: datetime
    category: CategoryBrief | None
    tags: list[TagBrief]


class AdminArticleListResponse(BaseModel):
    items: list[AdminArticleListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class PublicArticleListResponse(BaseModel):
    items: list[PublicArticleListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
