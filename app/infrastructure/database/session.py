from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# Engine 创建时不会真正连接数据库，首次执行 SQL 时才建连接，
# 因此应用启动与健康检查不依赖 MySQL 可用。
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI 依赖注入：提供请求级 Session，请求结束后自动关闭。

    事务由 Service 层统一控制（commit / rollback），此处只负责生命周期。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
