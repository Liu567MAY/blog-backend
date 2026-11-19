from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class CategoryPublicResponse(CategoryResponse):
    article_count: int


class CategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
