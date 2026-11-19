from fastapi.testclient import TestClient

ADMIN_CATEGORIES_URL = "/api/v1/admin/categories"
PUBLIC_CATEGORIES_URL = "/api/v1/categories"
ADMIN_ARTICLES_URL = "/api/v1/admin/articles"


def _create_category(
    client: TestClient,
    auth_headers: dict[str, str],
    name: str,
    *,
    slug: str | None = None,
    description: str | None = None,
) -> dict:
    payload: dict[str, object] = {"name": name}
    if slug is not None:
        payload["slug"] = slug
    if description is not None:
        payload["description"] = description
    response = client.post(ADMIN_CATEGORIES_URL, json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_article(
    client: TestClient,
    auth_headers: dict[str, str],
    *,
    title: str,
    slug: str,
    status: str,
    category_id: int | None = None,
) -> dict:
    payload: dict[str, object] = {
        "title": title,
        "slug": slug,
        "content_markdown": "# Body",
        "status": status,
    }
    if category_id is not None:
        payload["category_id"] = category_id
    response = client.post(ADMIN_ARTICLES_URL, json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_category_admin_endpoints_require_auth(client: TestClient) -> None:
    assert client.get(ADMIN_CATEGORIES_URL).status_code == 401
    assert client.post(ADMIN_CATEGORIES_URL, json={"name": "AI"}).status_code == 401
    assert client.patch(f"{ADMIN_CATEGORIES_URL}/1", json={"name": "New"}).status_code == 401
    assert client.delete(f"{ADMIN_CATEGORIES_URL}/1").status_code == 401


def test_create_category_with_auto_slug(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        ADMIN_CATEGORIES_URL,
        json={"name": "AI Agent", "description": "智能体"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "AI Agent"
    assert data["slug"] == "ai-agent"
    assert data["description"] == "智能体"
    assert data["created_at"]
    assert data["updated_at"]


def test_create_category_with_manual_slug(client: TestClient, auth_headers: dict[str, str]) -> None:
    category = _create_category(
        client, auth_headers, "Backend", slug="backend-dev", description="后端"
    )

    assert category["slug"] == "backend-dev"


def test_create_chinese_category_gets_safe_slug(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    category = _create_category(client, auth_headers, "人工智能")

    assert category["slug"]
    assert category["slug"].replace("-", "").isalnum()


def test_create_category_rejects_duplicate_name_and_slug(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _create_category(client, auth_headers, "AI", slug="ai")

    duplicate_name = client.post(
        ADMIN_CATEGORIES_URL, json={"name": "AI", "slug": "other"}, headers=auth_headers
    )
    duplicate_slug = client.post(
        ADMIN_CATEGORIES_URL, json={"name": "Other", "slug": "ai"}, headers=auth_headers
    )

    assert duplicate_name.status_code == 409
    assert duplicate_slug.status_code == 409


def test_admin_category_list_returns_categories(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    _create_category(client, auth_headers, "AI", slug="ai")
    _create_category(client, auth_headers, "Backend", slug="backend")

    response = client.get(ADMIN_CATEGORIES_URL, headers=auth_headers)

    assert response.status_code == 200
    assert {item["slug"] for item in response.json()} == {"ai", "backend"}


def test_update_category_fields_and_clear_description(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    category = _create_category(
        client, auth_headers, "AI", slug="ai", description="old description"
    )

    response = client.patch(
        f"{ADMIN_CATEGORIES_URL}/{category['id']}",
        json={"name": "AI & ML", "slug": "ai-ml", "description": None},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "AI & ML"
    assert data["slug"] == "ai-ml"
    assert data["description"] is None


def test_update_category_rejects_duplicates_and_invalid_values(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = _create_category(client, auth_headers, "First", slug="first")
    _create_category(client, auth_headers, "Second", slug="second")

    duplicate_name = client.patch(
        f"{ADMIN_CATEGORIES_URL}/{first['id']}",
        json={"name": "Second"},
        headers=auth_headers,
    )
    duplicate_slug = client.patch(
        f"{ADMIN_CATEGORIES_URL}/{first['id']}",
        json={"slug": "second"},
        headers=auth_headers,
    )
    empty_patch = client.patch(
        f"{ADMIN_CATEGORIES_URL}/{first['id']}", json={}, headers=auth_headers
    )
    bad_slug = client.patch(
        f"{ADMIN_CATEGORIES_URL}/{first['id']}",
        json={"slug": "Bad Slug!"},
        headers=auth_headers,
    )

    assert duplicate_name.status_code == 409
    assert duplicate_slug.status_code == 409
    assert empty_patch.status_code == 422
    assert bad_slug.status_code == 422


def test_update_missing_category_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"{ADMIN_CATEGORIES_URL}/999999", json={"name": "Ghost"}, headers=auth_headers
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "分类不存在"


def test_delete_unused_category(client: TestClient, auth_headers: dict[str, str]) -> None:
    category = _create_category(client, auth_headers, "Temporary", slug="temporary")

    response = client.delete(f"{ADMIN_CATEGORIES_URL}/{category['id']}", headers=auth_headers)

    assert response.status_code == 204
    assert response.content == b""
    listing = client.get(ADMIN_CATEGORIES_URL, headers=auth_headers).json()
    assert all(item["id"] != category["id"] for item in listing)


def test_delete_category_in_use_returns_409(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    category = _create_category(client, auth_headers, "In Use", slug="in-use")
    _create_article(
        client,
        auth_headers,
        title="Uses Category",
        slug="uses-category",
        status="draft",
        category_id=category["id"],
    )

    response = client.delete(f"{ADMIN_CATEGORIES_URL}/{category['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert "无法删除" in response.json()["detail"]


def test_delete_missing_category_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete(f"{ADMIN_CATEGORIES_URL}/999999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "分类不存在"


def test_public_categories_only_include_published_usage(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    published_category = _create_category(client, auth_headers, "Published", slug="published")
    draft_category = _create_category(client, auth_headers, "Draft", slug="draft-only")
    unused_category = _create_category(client, auth_headers, "Unused", slug="unused")

    _create_article(
        client,
        auth_headers,
        title="Published",
        slug="published-article",
        status="published",
        category_id=published_category["id"],
    )
    _create_article(
        client,
        auth_headers,
        title="Draft",
        slug="draft-article",
        status="draft",
        category_id=published_category["id"],
    )
    _create_article(
        client,
        auth_headers,
        title="Only Draft",
        slug="only-draft-article",
        status="draft",
        category_id=draft_category["id"],
    )

    response = client.get(PUBLIC_CATEGORIES_URL)

    assert response.status_code == 200
    items = response.json()
    assert [item["id"] for item in items] == [published_category["id"]]
    assert items[0]["article_count"] == 1
    assert unused_category["id"] not in [item["id"] for item in items]
