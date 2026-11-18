import re

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app

MEDIA_URL = "/api/v1/admin/media/upload-signature"


class FakeOssClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def sign_url(
        self,
        method: str,
        key: str,
        expires: int,
        headers: dict[str, str] | None = None,
        **_: object,
    ) -> str:
        self.calls.append({"method": method, "key": key, "expires": expires, "headers": headers})
        return f"https://bucket.oss-cn-hangzhou.aliyuncs.com/{key}?mock-signature"


def _configured_settings() -> Settings:
    return Settings(
        jwt_secret_key="test-secret-key",
        oss_bucket="test-bucket",
        oss_endpoint="https://oss-cn-hangzhou.aliyuncs.com",
        oss_region="cn-hangzhou",
        oss_access_key_id="test-access-key-id",
        oss_access_key_secret="test-access-key-secret",
        oss_public_base_url="https://img.example.com",
    )


def test_upload_signature_requires_auth(client: TestClient) -> None:
    response = client.post(
        MEDIA_URL,
        json={"filename": "photo.png", "content_type": "image/png", "size": 1024},
    )

    assert response.status_code == 401


def test_upload_signature_rejects_illegal_image_type(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        MEDIA_URL,
        json={"filename": "payload.svg", "content_type": "image/svg+xml", "size": 1024},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_upload_signature_rejects_oversized_image(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        MEDIA_URL,
        json={
            "filename": "large.png",
            "content_type": "image/png",
            "size": 10 * 1024 * 1024 + 1,
        },
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert "10MB" in response.json()["detail"]


def test_upload_signature_reports_missing_oss_config(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(jwt_secret_key="test-secret-key")

    response = client.post(
        MEDIA_URL,
        json={"filename": "photo.png", "content_type": "image/png", "size": 1024},
        headers=auth_headers,
    )

    assert response.status_code == 503
    assert "OSS" in response.json()["detail"]


def test_upload_signature_returns_presigned_put_and_public_url(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    fake = FakeOssClient()
    app.dependency_overrides[get_settings] = _configured_settings
    monkeypatch.setattr("app.modules.media.service.build_oss_client", lambda _: fake)

    response = client.post(
        MEDIA_URL,
        json={"filename": "我的照片.png", "content_type": "image/png", "size": 1024},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["method"] == "PUT"
    assert data["headers"] == {"Content-Type": "image/png"}
    assert data["object_key"].startswith("articles/")
    assert re.fullmatch(r"articles/\d{4}/\d{2}/[0-9a-f]{32}\.png", data["object_key"])
    assert data["public_url"] == f"https://img.example.com/{data['object_key']}"
    assert data["upload_url"].startswith("https://bucket.oss-cn-hangzhou.aliyuncs.com/")
    assert data["expires_in"] == 300
    assert fake.calls == [
        {
            "method": "PUT",
            "key": data["object_key"],
            "expires": 300,
            "headers": {"Content-Type": "image/png"},
        }
    ]


def test_upload_signature_uses_unique_safe_keys(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    fake = FakeOssClient()
    app.dependency_overrides[get_settings] = _configured_settings
    monkeypatch.setattr("app.modules.media.service.build_oss_client", lambda _: fake)

    first = client.post(
        MEDIA_URL,
        json={"filename": "../../evil.webp", "content_type": "image/webp", "size": 10},
        headers=auth_headers,
    )
    second = client.post(
        MEDIA_URL,
        json={"filename": "../../evil.webp", "content_type": "image/webp", "size": 10},
        headers=auth_headers,
    )

    assert first.status_code == second.status_code == 200
    first_key = first.json()["object_key"]
    second_key = second.json()["object_key"]
    assert first_key != second_key
    assert "evil" not in first_key
    assert ".." not in first_key
    assert first_key.endswith(".webp")

    jpeg = client.post(
        MEDIA_URL,
        json={"filename": "photo.jpeg", "content_type": "image/jpeg", "size": 10},
        headers=auth_headers,
    )
    gif = client.post(
        MEDIA_URL,
        json={"filename": "photo.gif", "content_type": "image/gif", "size": 10},
        headers=auth_headers,
    )
    assert jpeg.json()["object_key"].endswith(".jpg")
    assert gif.json()["object_key"].endswith(".gif")
