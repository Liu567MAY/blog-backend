import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.modules.auth import service
from app.modules.auth.models import AdminUser

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "s3cret-pass"


@pytest.fixture
def admin(db_session: Session) -> AdminUser:
    admin = AdminUser(username=ADMIN_USERNAME, password_hash=hash_password(ADMIN_PASSWORD))
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def test_login_success(client: TestClient, admin: AdminUser) -> None:
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_wrong_password(client: TestClient, admin: AdminUser) -> None:
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": ADMIN_USERNAME, "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"


def test_login_unknown_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "nobody", "password": "whatever"},
    )
    assert response.status_code == 401


def test_create_admin_single_mode(db_session: Session, admin: AdminUser) -> None:
    with pytest.raises(ConflictError):
        service.create_admin(db_session, "another", "password123")
