from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.articles.models import Article

ARTICLES_URL = "/api/v1/admin/articles"


def test_create_requires_auth(client: TestClient) -> None:
    response = client.post(ARTICLES_URL, json={"title": "hello"})
    assert response.status_code == 401


def test_create_rejects_invalid_token(client: TestClient) -> None:
    response = client.post(
        ARTICLES_URL, json={"title": "hello"}, headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


def test_create_draft_with_empty_content(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(ARTICLES_URL, json={"title": "My First Post"}, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["slug"] == "my-first-post"
    assert data["published_at"] is None
    assert data["created_at"]
    assert data["updated_at"]


def test_create_published(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        ARTICLES_URL,
        json={"title": "Published Post", "content_markdown": "# hi", "status": "published"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "published"
    assert data["published_at"] is not None


def test_publish_empty_content_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        ARTICLES_URL,
        json={"title": "No Body", "content_markdown": "   ", "status": "published"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_blank_title_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(ARTICLES_URL, json={"title": "   "}, headers=auth_headers)
    assert response.status_code == 422


def test_invalid_status_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        ARTICLES_URL, json={"title": "x", "status": "archived"}, headers=auth_headers
    )
    assert response.status_code == 422


def test_duplicate_manual_slug_conflict(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {"title": "A", "slug": "same-slug"}
    assert client.post(ARTICLES_URL, json=payload, headers=auth_headers).status_code == 201
    response = client.post(
        ARTICLES_URL, json={"title": "B", "slug": "same-slug"}, headers=auth_headers
    )
    assert response.status_code == 409


def test_invalid_manual_slug_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        ARTICLES_URL, json={"title": "A", "slug": "Bad Slug!"}, headers=auth_headers
    )
    assert response.status_code == 422


def test_auto_slug_deduplicates(client: TestClient, auth_headers: dict[str, str]) -> None:
    first = client.post(ARTICLES_URL, json={"title": "Repeat Title"}, headers=auth_headers)
    second = client.post(ARTICLES_URL, json={"title": "Repeat Title"}, headers=auth_headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["slug"] == "repeat-title"
    assert second.json()["slug"] == "repeat-title-2"


def test_chinese_title_generates_nonempty_slug(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(ARTICLES_URL, json={"title": "你好，世界"}, headers=auth_headers)
    assert response.status_code == 201
    slug = response.json()["slug"]
    assert slug
    assert slug.replace("-", "").isalnum()


def test_markdown_stored_verbatim(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    markdown = "# 标题\n\n- 列表项\n\n```python\nprint('你好')\n```\n"
    response = client.post(
        ARTICLES_URL,
        json={"title": "Markdown 原文", "content_markdown": markdown},
        headers=auth_headers,
    )
    assert response.status_code == 201
    article = db_session.get(Article, response.json()["id"])
    assert article is not None
    assert article.content_markdown == markdown
