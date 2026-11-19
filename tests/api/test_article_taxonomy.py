from fastapi.testclient import TestClient

ADMIN_ARTICLES_URL = "/api/v1/admin/articles"
ADMIN_CATEGORIES_URL = "/api/v1/admin/categories"
ADMIN_TAGS_URL = "/api/v1/admin/tags"


def _create_category(
    client: TestClient, auth_headers: dict[str, str], name: str, slug: str
) -> dict:
    response = client.post(
        ADMIN_CATEGORIES_URL, json={"name": name, "slug": slug}, headers=auth_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_tag(client: TestClient, auth_headers: dict[str, str], name: str, slug: str) -> dict:
    response = client.post(ADMIN_TAGS_URL, json={"name": name, "slug": slug}, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def _create_article(
    client: TestClient,
    auth_headers: dict[str, str],
    *,
    title: str = "Article",
    slug: str = "article",
    status: str = "draft",
    category_id: int | None = None,
    tag_ids: list[int] | None = None,
) -> dict:
    payload: dict[str, object] = {
        "title": title,
        "slug": slug,
        "content_markdown": "# Body",
        "status": status,
    }
    if category_id is not None:
        payload["category_id"] = category_id
    if tag_ids is not None:
        payload["tag_ids"] = tag_ids
    response = client.post(ADMIN_ARTICLES_URL, json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


def _detail(client: TestClient, auth_headers: dict[str, str], article_id: int) -> dict:
    response = client.get(f"{ADMIN_ARTICLES_URL}/{article_id}", headers=auth_headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_create_article_with_category_and_multiple_tags(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    category = _create_category(client, auth_headers, "AI", "ai")
    tag1 = _create_tag(client, auth_headers, "LangGraph", "langgraph")
    tag2 = _create_tag(client, auth_headers, "FastAPI", "fastapi")

    article = _create_article(
        client,
        auth_headers,
        category_id=category["id"],
        tag_ids=[tag1["id"], tag2["id"]],
    )
    data = _detail(client, auth_headers, article["id"])

    assert data["category"]["id"] == category["id"]
    assert data["category"]["name"] == "AI"
    assert data["category"]["slug"] == "ai"
    assert [tag["id"] for tag in data["tags"]] == [tag1["id"], tag2["id"]]
    assert [tag["slug"] for tag in data["tags"]] == ["langgraph", "fastapi"]


def test_create_article_without_taxonomy_returns_empty_associations(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    article = _create_article(client, auth_headers)

    data = _detail(client, auth_headers, article["id"])

    assert data["category"] is None
    assert data["tags"] == []


def test_create_article_deduplicates_tag_ids(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    tag = _create_tag(client, auth_headers, "Python", "python")
    article = _create_article(client, auth_headers, tag_ids=[tag["id"], tag["id"]])

    data = _detail(client, auth_headers, article["id"])

    assert [item["id"] for item in data["tags"]] == [tag["id"]]


def test_create_article_rejects_missing_category_without_writing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        ADMIN_ARTICLES_URL,
        json={"title": "Bad Category", "slug": "bad-category", "category_id": 999999},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert "分类不存在" in response.json()["detail"]
    listing = client.get(ADMIN_ARTICLES_URL, headers=auth_headers).json()
    assert listing["total"] == 0


def test_create_article_rejects_missing_tag_without_writing(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        ADMIN_ARTICLES_URL,
        json={"title": "Bad Tag", "slug": "bad-tag", "tag_ids": [999999]},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert "标签不存在" in response.json()["detail"]
    listing = client.get(ADMIN_ARTICLES_URL, headers=auth_headers).json()
    assert listing["total"] == 0


def test_patch_article_changes_category(client: TestClient, auth_headers: dict[str, str]) -> None:
    old = _create_category(client, auth_headers, "Old", "old")
    new = _create_category(client, auth_headers, "New", "new")
    article = _create_article(client, auth_headers, category_id=old["id"])

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article['id']}",
        json={"category_id": new["id"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["category"]["id"] == new["id"]


def test_patch_article_clears_category_with_null(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    category = _create_category(client, auth_headers, "AI", "ai")
    article = _create_article(client, auth_headers, category_id=category["id"])

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article['id']}",
        json={"category_id": None},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["category"] is None


def test_patch_article_without_category_keeps_it(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    category = _create_category(client, auth_headers, "AI", "ai")
    article = _create_article(client, auth_headers, category_id=category["id"])

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article['id']}",
        json={"title": "Only title changed"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["category"]["id"] == category["id"]


def test_patch_article_replaces_tags(client: TestClient, auth_headers: dict[str, str]) -> None:
    tag1 = _create_tag(client, auth_headers, "One", "one")
    tag2 = _create_tag(client, auth_headers, "Two", "two")
    tag3 = _create_tag(client, auth_headers, "Three", "three")
    article = _create_article(client, auth_headers, tag_ids=[tag1["id"], tag2["id"]])

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article['id']}",
        json={"tag_ids": [tag2["id"], tag3["id"]]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert [tag["id"] for tag in response.json()["tags"]] == [tag2["id"], tag3["id"]]


def test_patch_article_clears_tags_with_empty_list(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    tag = _create_tag(client, auth_headers, "One", "one")
    article = _create_article(client, auth_headers, tag_ids=[tag["id"]])

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article['id']}",
        json={"tag_ids": []},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["tags"] == []


def test_patch_article_without_tags_keeps_them(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    tag = _create_tag(client, auth_headers, "One", "one")
    article = _create_article(client, auth_headers, tag_ids=[tag["id"]])

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article['id']}",
        json={"summary": "New summary"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["tags"]] == [tag["id"]]


def test_patch_article_rejects_unknown_associations(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    tag = _create_tag(client, auth_headers, "One", "one")
    article = _create_article(client, auth_headers, tag_ids=[tag["id"]])

    missing_category = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article['id']}",
        json={"category_id": 999999},
        headers=auth_headers,
    )
    missing_tag = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article['id']}",
        json={"tag_ids": [999999]},
        headers=auth_headers,
    )

    assert missing_category.status_code == 422
    assert missing_tag.status_code == 422
    data = _detail(client, auth_headers, article["id"])
    assert data["category"] is None
    assert [item["id"] for item in data["tags"]] == [tag["id"]]


def test_patch_article_rejects_null_tag_ids(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    article = _create_article(client, auth_headers)

    response = client.patch(
        f"{ADMIN_ARTICLES_URL}/{article['id']}",
        json={"tag_ids": None},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_public_detail_returns_category_and_tags(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    category = _create_category(client, auth_headers, "AI", "ai")
    tag = _create_tag(client, auth_headers, "LangGraph", "langgraph")
    _create_article(
        client,
        auth_headers,
        title="Published",
        slug="published-taxonomy",
        status="published",
        category_id=category["id"],
        tag_ids=[tag["id"]],
    )

    response = client.get("/api/v1/articles/published-taxonomy")

    assert response.status_code == 200
    data = response.json()
    assert data["category"]["slug"] == "ai"
    assert data["tags"][0]["slug"] == "langgraph"
