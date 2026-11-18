from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.articles.models import Article, ArticleStatus

ADMIN_ARTICLES_URL = "/api/v1/admin/articles"
PUBLIC_ARTICLES_URL = "/api/v1/articles"

_CREATED_AT = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
_PUBLISHED_AT = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)


def _add_article(
    db: Session,
    *,
    title: str = "Original",
    slug: str = "original",
    summary: str | None = "Original summary",
    content_markdown: str = "# Original\n\nBody",
    status: ArticleStatus = ArticleStatus.DRAFT,
    published_at: datetime | None = None,
) -> Article:
    article = Article(
        title=title,
        slug=slug,
        summary=summary,
        content_markdown=content_markdown,
        status=status,
        created_at=_CREATED_AT,
        updated_at=_CREATED_AT,
        published_at=published_at,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def test_update_requires_auth(client: TestClient) -> None:
    response = client.patch(f"{ADMIN_ARTICLES_URL}/1", json={"title": "Updated"})
    assert response.status_code == 401


def test_update_missing_article_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/999999", json={"title": "Updated"}, headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "文章不存在"


def test_update_title_preserves_omitted_fields(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(db_session)

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}", json={"title": "Renamed"}, headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Renamed"
    assert data["slug"] == "original"
    assert data["summary"] == "Original summary"
    assert data["content_markdown"] == "# Original\n\nBody"
    assert data["status"] == "draft"
    assert data["published_at"] is None


def test_update_persists_markdown_and_touches_updated_at(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(db_session)
    old_updated_at = article.updated_at

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}",
        json={"content_markdown": "# Updated\n\n新正文"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["content_markdown"] == "# Updated\n\n新正文"
    db_session.expire_all()
    updated = db_session.get(Article, article.id)
    assert updated is not None
    assert updated.content_markdown == "# Updated\n\n新正文"
    assert updated.updated_at > old_updated_at


def test_update_all_fields_and_publish(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(db_session)

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}",
        json={
            "title": "New Title",
            "slug": "new-title",
            "summary": "New summary",
            "content_markdown": "# New\n\nPublished body",
            "status": "published",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["slug"] == "new-title"
    assert data["summary"] == "New summary"
    assert data["content_markdown"] == "# New\n\nPublished body"
    assert data["status"] == "published"
    assert data["published_at"] is not None

    public = client.get(f"{PUBLIC_ARTICLES_URL}/new-title")
    assert public.status_code == 200
    assert public.json()["content_markdown"] == "# New\n\nPublished body"


def test_update_can_clear_summary_with_null(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(db_session)

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}", json={"summary": None}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["summary"] is None


def test_update_duplicate_slug_returns_409(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    first = _add_article(db_session, title="First", slug="first")
    _add_article(db_session, title="Second", slug="second")

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{first.id}", json={"slug": "second"}, headers=auth_headers
    )

    assert response.status_code == 409
    assert "slug 已存在" in response.json()["detail"]


def test_update_with_same_slug_is_allowed(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(db_session, slug="same-slug")

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}",
        json={"slug": "same-slug", "title": "Changed"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "same-slug"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "   "},
        {"title": None},
        {"slug": "Bad Slug!"},
        {"slug": None},
        {"content_markdown": None},
        {"status": None},
        {"status": "archived"},
    ],
)
def test_update_rejects_invalid_payload(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
    payload: dict[str, object],
) -> None:
    article = _add_article(db_session)

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}", json=payload, headers=auth_headers
    )

    assert response.status_code == 422


def test_first_publish_sets_published_at(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(db_session, content_markdown="# Ready")

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}", json={"status": "published"}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert response.json()["published_at"] is not None


def test_update_published_article_preserves_published_at(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(
        db_session,
        status=ArticleStatus.PUBLISHED,
        published_at=_PUBLISHED_AT,
        content_markdown="# Published",
    )
    original_published_at = article.published_at

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}",
        json={"title": "Published Updated"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["published_at"] == original_published_at.isoformat()


def test_withdraw_to_draft_clears_published_at(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(
        db_session,
        status=ArticleStatus.PUBLISHED,
        published_at=_PUBLISHED_AT,
        content_markdown="# Published",
    )

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}", json={"status": "draft"}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "draft"
    assert response.json()["published_at"] is None


def test_publish_with_empty_content_is_rejected(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(db_session, content_markdown="   ")

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}", json={"status": "published"}, headers=auth_headers
    )

    assert response.status_code == 422
    assert "正文" in response.json()["detail"]


def test_published_article_cannot_be_saved_with_empty_content(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(
        db_session,
        status=ArticleStatus.PUBLISHED,
        published_at=_PUBLISHED_AT,
        content_markdown="# Published",
    )

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article.id}",
        json={"content_markdown": "   "},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_delete_requires_auth(client: TestClient, db_session: Session) -> None:
    article = _add_article(db_session)

    response = client.delete(f"{ADMIN_ARTICLES_URL}/{article.id}")

    assert response.status_code == 401


def test_delete_removes_article_from_admin_and_public_queries(
    client: TestClient, auth_headers: dict[str, str], db_session: Session
) -> None:
    article = _add_article(
        db_session,
        status=ArticleStatus.PUBLISHED,
        published_at=_PUBLISHED_AT,
        content_markdown="# Published",
        slug="delete-me",
    )

    response = client.delete(f"{ADMIN_ARTICLES_URL}/{article.id}", headers=auth_headers)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"{ADMIN_ARTICLES_URL}/{article.id}", headers=auth_headers).status_code == 404
    assert client.get(f"{PUBLIC_ARTICLES_URL}/delete-me").status_code == 404
    public_list = client.get(f"{PUBLIC_ARTICLES_URL}?page_size=100")
    assert "delete-me" not in [item["slug"] for item in public_list.json()["items"]]
    admin_list = client.get(f"{ADMIN_ARTICLES_URL}?page_size=100", headers=auth_headers)
    assert admin_list.json()["total"] == 0


def test_delete_missing_article_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete(f"{ADMIN_ARTICLES_URL}/999999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "文章不存在"
