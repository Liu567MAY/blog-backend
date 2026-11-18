from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError:
        return False


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> str:
    """校验 JWT 并返回 subject（管理员 ID），失败抛 AuthenticationError。"""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret_key, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise AuthenticationError("无效或已过期的登录凭证") from None
    subject = payload.get("sub")
    if not subject:
        raise AuthenticationError("无效或已过期的登录凭证")
    return subject
