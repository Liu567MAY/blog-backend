from fastapi.testclient import TestClient

ADMIN_TAGS_URL = "/api/v1/admin/tags"
PUBLIC_TAGS_URL = "/api/v1/tags"
ADMIN_ARTICLES_URL = "/api/v1/admin/articles"


def _create_tag(
    client: TestClient,
    auth_headers: dict[str, str],
    name: str,
    *,
    slug: str | None = None,
) -> dict:
    payload: dict[str, object] = {"name": name}
    if slug is not None:
        payload["slug"] = slug
    response = client.post(ADMIN_TAGS_URL, json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_article(
    client: TestClient,
    auth_headers: dict[str, str],
    *,
    title: str,
    slug: str,
    status: str,
    tag_ids: list[int] | None = None,
) -> dict:
    payload: dict[str, object] = {
        "title": title,
        "slug": slug,
        "content_markdown": "# Body",
        "status": status,
    }
    if tag_ids is not None:
        payload["tag_ids"] = tag_ids
    response = client.post(ADMIN_ARTICLES_URL, json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_tag_admin_endpoints_require_auth(client: TestClient) -> None:
    assert client.get(ADMIN_TAGS_URL).status_code == 401
    assert client.post(ADMIN_TAGS_URL, json={"name": "Python"}).status_code == 401
    assert client.patch(f"{ADMIN_TAGS_URL}/1", json={"name": "New"}).status_code == 401
    assert client.delete(f"{ADMIN_TAGS_URL}/1").status_code == 401


def test_create_tag_with_auto_slug(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(ADMIN_TAGS_URL, json={"name": "Fast API"}, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Fast API"
    assert data["slug"] == "fast-api"
    assert data["created_at"]
    assert data["updated_at"]


def test_create_tag_with_manual_slug(client: TestClient, auth_headers: dict[str, str]) -> None:
    tag = _create_tag(client, auth_headers, "LangGraph", slug="lang-graph")

    assert tag["slug"] == "lang-graph"


def test_create_chinese_tag_gets_safe_slug(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    tag = _create_tag(client, auth_headers, "机器学习")

    assert tag["slug"]
    assert tag["slug"].replace("-", "").isalnum()


def test_create_tag_rejects_duplicate_name_and_slug(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _create_tag(client, auth_headers, "Python", slug="python")

    duplicate_name = client.post(
        ADMIN_TAGS_URL, json={"name": "Python", "slug": "python-2"}, headers=auth_headers
    )
    duplicate_slug = client.post(
        ADMIN_TAGS_URL, json={"name": "Python 2", "slug": "python"}, headers=auth_headers
    )

    assert duplicate_name.status_code == 409
    assert duplicate_slug.status_code == 409


def test_admin_tag_list_returns_tags(client: TestClient, auth_headers: dict[str, str]) -> None:
    _create_tag(client, auth_headers, "Python", slug="python")
    _create_tag(client, auth_headers, "FastAPI", slug="fastapi")

    response = client.get(ADMIN_TAGS_URL, headers=auth_headers)

    assert response.status_code == 200
    assert {item["slug"] for item in response.json()} == {"python", "fastapi"}


def test_update_tag_fields(client: TestClient, auth_headers: dict[str, str]) -> None:
    tag = _create_tag(client, auth_headers, "Old", slug="old")

    response = client.patch(
        f"{ADMIN_TAGS_URL}/{tag['id']}",
        json={"name": "New", "slug": "new"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New"
    assert response.json()["slug"] == "new"


def test_update_tag_rejects_duplicates_and_invalid_values(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = _create_tag(client, auth_headers, "First", slug="first")
    _create_tag(client, auth_headers, "Second", slug="second")

    duplicate_name = client.patch(
        f"{ADMIN_TAGS_URL}/{first['id']}", json={"name": "Second"}, headers=auth_headers
    )
    duplicate_slug = client.patch(
        f"{ADMIN_TAGS_URL}/{first['id']}", json={"slug": "second"}, headers=auth_headers
    )
    empty_patch = client.patch(f"{ADMIN_TAGS_URL}/{first['id']}", json={}, headers=auth_headers)
    bad_slug = client.patch(
        f"{ADMIN_TAGS_URL}/{first['id']}", json={"slug": "Bad Slug!"}, headers=auth_headers
    )

    assert duplicate_name.status_code == 409
    assert duplicate_slug.status_code == 409
    assert empty_patch.status_code == 422
    assert bad_slug.status_code == 422


def test_update_missing_tag_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.patch(
        f"{ADMIN_TAGS_URL}/999999", json={"name": "Ghost"}, headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "标签不存在"


def test_delete_unused_tag(client: TestClient, auth_headers: dict[str, str]) -> None:
    tag = _create_tag(client, auth_headers, "Temporary", slug="temporary")

    response = client.delete(f"{ADMIN_TAGS_URL}/{tag['id']}", headers=auth_headers)

    assert response.status_code == 204
    assert response.content == b""
    listing = client.get(ADMIN_TAGS_URL, headers=auth_headers).json()
    assert all(item["id"] != tag["id"] for item in listing)


def test_delete_tag_in_use_returns_409(client: TestClient, auth_headers: dict[str, str]) -> None:
    tag = _create_tag(client, auth_headers, "In Use", slug="in-use")
    _create_article(
        client,
        auth_headers,
        title="Uses Tag",
        slug="uses-tag",
        status="draft",
        tag_ids=[tag["id"]],
    )

    response = client.delete(f"{ADMIN_TAGS_URL}/{tag['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert "无法删除" in response.json()["detail"]


def test_delete_missing_tag_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.delete(f"{ADMIN_TAGS_URL}/999999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "标签不存在"


def test_public_tags_only_include_published_usage(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    published_tag = _create_tag(client, auth_headers, "Published", slug="published-tag")
    draft_tag = _create_tag(client, auth_headers, "Draft", slug="draft-tag")
    unused_tag = _create_tag(client, auth_headers, "Unused", slug="unused-tag")

    _create_article(
        client,
        auth_headers,
        title="Published",
        slug="published-tag-article",
        status="published",
        tag_ids=[published_tag["id"]],
    )
    _create_article(
        client,
        auth_headers,
        title="Draft",
        slug="draft-tag-article",
        status="draft",
        tag_ids=[published_tag["id"]],
    )
    _create_article(
        client,
        auth_headers,
        title="Only Draft",
        slug="only-draft-tag-article",
        status="draft",
        tag_ids=[draft_tag["id"]],
    )

    response = client.get(PUBLIC_TAGS_URL)

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [published_tag["id"]]
    assert items[0]["article_count"] == 1
    assert unused_tag["id"] not in [item["id"] for item in items]
