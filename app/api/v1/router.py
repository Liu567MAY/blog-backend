from fastapi import APIRouter

from app.api.v1 import health
from app.api.v1.admin import article_autosaves as admin_article_autosaves
from app.api.v1.admin import articles as admin_articles
from app.api.v1.admin import auth as admin_auth
from app.api.v1.admin import categories as admin_categories
from app.api.v1.admin import media as admin_media
from app.api.v1.admin import tags as admin_tags
from app.api.v1.public import articles as public_articles
from app.api.v1.public import categories as public_categories
from app.api.v1.public import tags as public_tags

# V1 唯一路由聚合入口，直接注册各业务路由
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(admin_auth.router, prefix="/admin/auth", tags=["admin-auth"])
api_router.include_router(admin_articles.router, prefix="/admin/articles", tags=["admin-articles"])
api_router.include_router(
    admin_article_autosaves.router,
    prefix="/admin/article-autosaves",
    tags=["admin-article-autosaves"],
)
api_router.include_router(
    admin_categories.router, prefix="/admin/categories", tags=["admin-categories"]
)
api_router.include_router(admin_tags.router, prefix="/admin/tags", tags=["admin-tags"])
api_router.include_router(admin_media.router, prefix="/admin/media", tags=["admin-media"])
api_router.include_router(public_articles.router, prefix="/articles", tags=["articles"])
api_router.include_router(public_categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(public_tags.router, prefix="/tags", tags=["tags"])
