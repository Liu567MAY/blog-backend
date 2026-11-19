from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AutosavePutRequest(BaseModel):
    title: str = Field(default="", max_length=200)
    slug: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    content_markdown: str = ""
    article_id: int | None = Field(default=None, ge=1)
    revision: int = Field(default=0, ge=0)


class AutosaveListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    article_id: int | None
    title: str
    slug: str | None
    summary: str | None
    revision: int
    created_at: datetime
    updated_at: datetime


class AutosaveResponse(AutosaveListItem):
    content_markdown: str
