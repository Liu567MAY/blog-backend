from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.articles.models import ArticleStatus


class ArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    content_markdown: str = ""
    status: ArticleStatus = ArticleStatus.DRAFT


class ArticleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    content_markdown: str | None = None
    status: ArticleStatus | None = None


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
