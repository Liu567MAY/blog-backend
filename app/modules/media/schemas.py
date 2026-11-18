from typing import Literal

from pydantic import BaseModel, Field

MediaContentType = Literal["image/png", "image/jpeg", "image/webp", "image/gif"]


class MediaUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: MediaContentType
    size: int = Field(gt=0, description="图片字节数")


class MediaUploadSignature(BaseModel):
    upload_url: str
    method: str = "PUT"
    headers: dict[str, str]
    object_key: str
    public_url: str
    expires_in: int
