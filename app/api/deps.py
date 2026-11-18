from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.infrastructure.database.session import get_db
from app.modules.auth import repository as auth_repository
from app.modules.auth.models import AdminUser

_bearer = HTTPBearer(auto_error=False)


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> AdminUser:
    """管理端通用鉴权依赖：校验 Bearer JWT 并返回当前管理员。"""
    if credentials is None:
        raise AuthenticationError("未提供登录凭证")
    subject = decode_access_token(credentials.credentials)
    try:
        admin_id = int(subject)
    except ValueError:
        raise AuthenticationError("无效或已过期的登录凭证") from None
    admin = auth_repository.get_by_id(db, admin_id)
    if admin is None:
        raise AuthenticationError("管理员不存在")
    return admin
