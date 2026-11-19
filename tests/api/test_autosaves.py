from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.auth.models import AdminUser

AUTOSAVES_URL = "/api/v1/admin/article-autosaves"
ARTICLES_URL = "/api/v1/admin/articles"


def _put_autosave(
    client: TestClient,
    auth_headers: dict[str, str],
    autosave_id,
    *,
    revision: int = 0,
    **fields,
):
    payload = {
        "title": "",
        "slug": None,
        "summary": None,
        "content_markdown": "",
        "article_id": None,
        "revision": revision,
        **fields,
    }
    return client.put(f"{AUTOSAVES_URL}/{autosave_id}", json=payload, headers=auth_headers)


def _create_article(
    client: TestClient,
    auth_headers: dict[str, str],
    *,
    title: str = "Article",
    slug: str = "article",
    status: str = "draft",
    content_markdown: str = "# Body",
    autosave_id=None,
) -> dict:
    payload = {
        "title": title,
        "slug": slug,
        "content_markdown": content_markdown,
        "status": status,
    }
    if autosave_id is not None:
        payload["autosave_id"] = str(autosave_id)
    response = client.post(ARTICLES_URL, json=payload, headers=auth_headers)
    return response


def _other_admin_headers(client: TestClient, db_session: Session) -> dict[str, str]:
    other = AdminUser(username="other", password_hash=hash_password("other-pass"))
    db_session.add(other)
    db_session.commit()
    response = client.post(
        "/api/v1/admin/auth/login", json={"username": "other", "password": "other-pass"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_autosave_endpoints_require_auth(client: TestClient) -> None:
    autosave_id = uuid4()
    assert client.get(AUTOSAVES_URL).status_code == 401
    assert client.get(f"{AUTOSAVES_URL}/{autosave_id}").status_code == 401
    assert client.put(f"{AUTOSAVES_URL}/{autosave_id}", json={}).status_code == 401
    assert client.delete(f"{AUTOSAVES_URL}/{autosave_id}").status_code == 401


def test_create_autosave_for_new_article(client: TestClient, auth_headers: dict[str, str]) -> None:
    autosave_id = uuid4()

    response = _put_autosave(
        client,
        auth_headers,
        autosave_id,
        title="未保存的新文章",
        slug="unsaved",
        summary="临时摘要",
        content_markdown="",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(autosave_id)
    assert data["revision"] == 1
    assert data["article_id"] is None
    assert data["updated_at"]
    listing = client.get(AUTOSAVES_URL, headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert "content_markdown" not in listing.json()[0]
    assert client.get(ARTICLES_URL, headers=auth_headers).json()["total"] == 0


def test_autosave_accepts_empty_title_and_body(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    autosave_id = uuid4()

    response = _put_autosave(client, auth_headers, autosave_id, title="", content_markdown="")

    assert response.status_code == 200
    snapshot = client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["title"] == ""
    assert snapshot.json()["content_markdown"] == ""


def test_autosave_restores_full_markdown(client: TestClient, auth_headers: dict[str, str]) -> None:
    autosave_id = uuid4()
    markdown = "# 临时标题\n\n中文正文\n\n```python\nprint('draft')\n```\n"

    _put_autosave(
        client,
        auth_headers,
        autosave_id,
        title="草稿标题",
        content_markdown=markdown,
    )
    snapshot = client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers)

    assert snapshot.status_code == 200
    assert snapshot.json()["content_markdown"] == markdown


def test_same_autosave_id_updates_existing_snapshot(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    autosave_id = uuid4()
    first = _put_autosave(client, auth_headers, autosave_id, content_markdown="v1")
    first_updated_at = first.json()["updated_at"]

    second = _put_autosave(
        client,
        auth_headers,
        autosave_id,
        revision=1,
        title="Updated",
        content_markdown="v2",
    )

    assert second.status_code == 200
    assert second.json()["revision"] == 2
    assert second.json()["updated_at"] >= first_updated_at
    listing = client.get(AUTOSAVES_URL, headers=auth_headers).json()
    assert len(listing) == 1
    snapshot = client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers)
    assert snapshot.json()["content_markdown"] == "v2"


def test_stale_revision_does_not_overwrite_newer_content(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    autosave_id = uuid4()
    _put_autosave(client, auth_headers, autosave_id, content_markdown="v1")
    _put_autosave(client, auth_headers, autosave_id, revision=1, content_markdown="v2")

    stale = _put_autosave(client, auth_headers, autosave_id, revision=1, content_markdown="stale")

    assert stale.status_code == 409
    snapshot = client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers)
    assert snapshot.json()["content_markdown"] == "v2"
    assert snapshot.json()["revision"] == 2


def test_first_save_with_nonzero_revision_is_conflict(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = _put_autosave(client, auth_headers, uuid4(), revision=3, content_markdown="bad")

    assert response.status_code == 409


def test_autosave_for_published_article_does_not_modify_article(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = _create_article(
        client,
        auth_headers,
        title="Published",
        slug="published",
        status="published",
        content_markdown="# Published",
    )
    article_id = created.json()["id"]
    before = client.get(f"{ARTICLES_URL}/{article_id}", headers=auth_headers).json()
    autosave_id = uuid4()

    response = _put_autosave(
        client,
        auth_headers,
        autosave_id,
        article_id=article_id,
        title="Unsaved title",
        content_markdown="# Unsaved secret",
    )

    assert response.status_code == 200
    after = client.get(f"{ARTICLES_URL}/{article_id}", headers=auth_headers).json()
    assert after["title"] == before["title"]
    assert after["content_markdown"] == before["content_markdown"]
    assert after["status"] == before["status"]
    assert after["published_at"] == before["published_at"]


def test_autosave_rejects_unknown_article_id(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = _put_autosave(client, auth_headers, uuid4(), article_id=999999, content_markdown="x")

    assert response.status_code == 422
    assert "文章不存在" in response.json()["detail"]


def test_create_article_cleans_up_autosave(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    autosave_id = uuid4()
    _put_autosave(client, auth_headers, autosave_id, title="Temporary")

    response = _create_article(
        client,
        auth_headers,
        title="Formal",
        slug="formal",
        autosave_id=autosave_id,
    )

    assert response.status_code == 201
    assert client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers).status_code == 404
    assert client.get(AUTOSAVES_URL, headers=auth_headers).json() == []


def test_update_article_cleans_up_autosave(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    article = _create_article(client, auth_headers, slug="update-target").json()
    autosave_id = uuid4()
    _put_autosave(
        client,
        auth_headers,
        autosave_id,
        article_id=article["id"],
        content_markdown="# Draft edit",
    )

    response = client.patch(
        f"{ARTICLES_URL}/{article['id']}",
        json={"title": "Formal update", "autosave_id": str(autosave_id)},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers).status_code == 404


def test_failed_formal_save_keeps_autosave(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _create_article(client, auth_headers, title="Existing", slug="duplicate")
    autosave_id = uuid4()
    _put_autosave(client, auth_headers, autosave_id, title="Unsaved")

    response = _create_article(
        client,
        auth_headers,
        title="Conflict",
        slug="duplicate",
        autosave_id=autosave_id,
    )

    assert response.status_code == 409
    snapshot = client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["content_markdown"] == ""


def test_delete_autosave_does_not_delete_article(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    article = _create_article(client, auth_headers, slug="keep-me").json()
    autosave_id = uuid4()
    _put_autosave(client, auth_headers, autosave_id, article_id=article["id"], title="Temp")

    response = client.delete(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers)

    assert response.status_code == 204
    assert client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers).status_code == 404
    assert client.get(f"{ARTICLES_URL}/{article['id']}", headers=auth_headers).status_code == 200


def test_deleting_article_removes_related_autosaves(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    article = _create_article(client, auth_headers, slug="delete-article").json()
    autosave_id = uuid4()
    _put_autosave(client, auth_headers, autosave_id, article_id=article["id"])

    response = client.delete(f"{ARTICLES_URL}/{article['id']}", headers=auth_headers)

    assert response.status_code == 204
    assert client.get(AUTOSAVES_URL, headers=auth_headers).json() == []


def test_autosave_list_filters_by_article_id(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    article = _create_article(client, auth_headers, slug="filter-target").json()
    related_id = uuid4()
    unrelated_id = uuid4()
    _put_autosave(client, auth_headers, related_id, article_id=article["id"])
    _put_autosave(client, auth_headers, unrelated_id)

    response = client.get(f"{AUTOSAVES_URL}?article_id={article['id']}", headers=auth_headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(related_id)]
    assert "content_markdown" not in response.json()[0]


def test_autosave_is_isolated_between_admins(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    autosave_id = uuid4()
    _put_autosave(client, auth_headers, autosave_id, content_markdown="admin one")
    other_headers = _other_admin_headers(client, db_session)

    assert client.get(AUTOSAVES_URL, headers=other_headers).json() == []
    assert client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=other_headers).status_code == 404
    assert client.delete(f"{AUTOSAVES_URL}/{autosave_id}", headers=other_headers).status_code == 404
    overwrite = _put_autosave(
        client,
        other_headers,
        autosave_id,
        revision=1,
        content_markdown="admin two",
    )
    assert overwrite.status_code == 404
    snapshot = client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers)
    assert snapshot.json()["content_markdown"] == "admin one"


def test_missing_autosave_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    autosave_id = uuid4()

    assert client.get(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers).status_code == 404
    assert client.delete(f"{AUTOSAVES_URL}/{autosave_id}", headers=auth_headers).status_code == 404
