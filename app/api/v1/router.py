from fastapi import APIRouter

from app.api.v1 import health
from app.api.v1.admin import articles as admin_articles
from app.api.v1.admin import auth as admin_auth

# V1 唯一路由聚合入口，直接注册各业务路由
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(admin_auth.router, prefix="/admin/auth", tags=["admin-auth"])
api_router.include_router(admin_articles.router, prefix="/admin/articles", tags=["admin-articles"])
