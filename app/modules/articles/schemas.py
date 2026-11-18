from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.articles.models import ArticleStatus


class ArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    content_markdown: str = ""
    status: ArticleStatus = ArticleStatus.DRAFT


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
