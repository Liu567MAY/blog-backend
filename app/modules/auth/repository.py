from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auth.models import AdminUser


def get_by_username(db: Session, username: str) -> AdminUser | None:
    return db.scalar(select(AdminUser).where(AdminUser.username == username))


def get_by_id(db: Session, admin_id: int) -> AdminUser | None:
    return db.get(AdminUser, admin_id)


def count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(AdminUser)) or 0


def add(db: Session, admin: AdminUser) -> None:
    db.add(admin)
    db.flush()
