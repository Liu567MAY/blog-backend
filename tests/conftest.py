import os
from collections.abc import Iterator

# 必须在导入 app 之前设置，Settings 带 lru_cache
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.infrastructure.database.base import Base  # noqa: E402
from app.infrastructure.database.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.articles import models as article_models  # noqa: F401, E402
from app.modules.auth import models as auth_models  # noqa: F401, E402
from app.modules.auth.models import AdminUser  # noqa: E402

# 测试专用 sqlite 内存库；生产表结构一律由 Alembic 管理


@pytest.fixture
def db_session() -> Iterator[Session]:
    # 每个用例独立建库，保证测试间数据隔离
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with testing_session() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    admin = AdminUser(username="admin", password_hash=hash_password("s3cret-pass"))
    db_session.add(admin)
    db_session.commit()
    response = client.post(
        "/api/v1/admin/auth/login", json={"username": "admin", "password": "s3cret-pass"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
