from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=200)


class TagUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=200)


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class TagPublicResponse(TagResponse):
    article_count: int


class TagBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
