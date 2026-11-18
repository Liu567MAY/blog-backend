from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth import repository
from app.modules.auth.models import AdminUser
from app.modules.auth.schemas import LoginRequest, TokenResponse


def login(db: Session, data: LoginRequest) -> TokenResponse:
    admin = repository.get_by_username(db, data.username)
    if admin is None or not verify_password(data.password, admin.password_hash):
        raise AuthenticationError("用户名或密码错误")
    return TokenResponse(access_token=create_access_token(str(admin.id)))


def create_admin(db: Session, username: str, password: str) -> AdminUser:
    """单管理员模式：已存在管理员时拒绝创建。事务由本层控制。"""
    if repository.count(db) > 0:
        raise ConflictError("管理员已存在，单管理员模式不允许重复初始化")
    admin = AdminUser(username=username, password_hash=hash_password(password))
    repository.add(db, admin)
    db.commit()
    db.refresh(admin)
    return admin
