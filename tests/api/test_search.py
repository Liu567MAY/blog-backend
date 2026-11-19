import pytest
from fastapi.testclient import TestClient

ADMIN_ARTICLES_URL = "/api/v1/admin/articles"
PUBLIC_ARTICLES_URL = "/api/v1/articles"
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
    title: str,
    slug: str,
    summary: str | None,
    content_markdown: str,
    status: str,
    category_id: int,
    tag_ids: list[int],
) -> dict:
    response = client.post(
        ADMIN_ARTICLES_URL,
        json={
            "title": title,
            "slug": slug,
            "summary": summary,
            "content_markdown": content_markdown,
            "status": status,
            "category_id": category_id,
            "tag_ids": tag_ids,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def search_data(client: TestClient, auth_headers: dict[str, str]) -> dict[str, dict]:
    ai = _create_category(client, auth_headers, "AI Agent", "ai-agent")
    backend = _create_category(client, auth_headers, "Backend", "backend")
    langgraph = _create_tag(client, auth_headers, "LangGraph", "langgraph")
    fastapi = _create_tag(client, auth_headers, "FastAPI", "fastapi")
    python = _create_tag(client, auth_headers, "Python", "python")

    first = _create_article(
        client,
        auth_headers,
        title="LangGraph 入门",
        slug="langgraph-intro",
        summary="图工作流基础",
        content_markdown="# LangGraph\n\nPython 和 FastAPI 示例",
        status="published",
        category_id=ai["id"],
        tag_ids=[langgraph["id"], fastapi["id"]],
    )
    second = _create_article(
        client,
        auth_headers,
        title="FastAPI 实战",
        slug="fastapi-practice",
        summary="后端开发，进度 1000",
        content_markdown="# FastAPI\n\nPython Web 开发",
        status="published",
        category_id=backend["id"],
        tag_ids=[fastapi["id"], python["id"]],
    )
    third = _create_article(
        client,
        auth_headers,
        title="中文搜索测试",
        slug="chinese-search",
        summary="特殊字符 100% 完成",
        content_markdown="# 中文正文\n\n关于机器学习",
        status="published",
        category_id=ai["id"],
        tag_ids=[langgraph["id"]],
    )
    draft = _create_article(
        client,
        auth_headers,
        title="LangGraph 草稿",
        slug="langgraph-draft",
        summary="不该出现在公开搜索",
        content_markdown="# Draft\n\nFastAPI secret",
        status="draft",
        category_id=ai["id"],
        tag_ids=[langgraph["id"]],
    )
    return {
        "ai": ai,
        "backend": backend,
        "langgraph": langgraph,
        "fastapi": fastapi,
        "python": python,
        "first": first,
        "second": second,
        "third": third,
        "draft": draft,
    }


def test_public_search_matches_title_and_excludes_drafts(
    client: TestClient, search_data: dict[str, dict]
) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?keyword=LangGraph")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert [item["slug"] for item in data["items"]] == ["langgraph-intro"]


def test_public_search_matches_summary(client: TestClient, search_data: dict[str, dict]) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?keyword=后端开发")

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["fastapi-practice"]


def test_public_search_matches_markdown_content(
    client: TestClient, search_data: dict[str, dict]
) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?keyword=机器学习")

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["chinese-search"]


def test_public_search_matches_chinese_text(
    client: TestClient, search_data: dict[str, dict]
) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?keyword=中文")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["slug"] == "chinese-search"


def test_public_search_escapes_percent_wildcard(
    client: TestClient, search_data: dict[str, dict]
) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?keyword=100%25")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert [item["slug"] for item in data["items"]] == ["chinese-search"]


def test_public_search_treats_sql_metacharacters_as_literal(
    client: TestClient, search_data: dict[str, dict]
) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?keyword=%27%20OR%201%3D1%20--")

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_public_search_filters_by_category(
    client: TestClient, search_data: dict[str, dict]
) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?category=ai-agent")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert [item["slug"] for item in data["items"]] == ["chinese-search", "langgraph-intro"]


def test_public_search_filters_by_tag(client: TestClient, search_data: dict[str, dict]) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?tag=langgraph")

    assert response.status_code == 200
    data = response.json()
    assert [item["slug"] for item in data["items"]] == ["chinese-search", "langgraph-intro"]


def test_public_search_combines_all_filters_with_and(
    client: TestClient, search_data: dict[str, dict]
) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?keyword=Python&category=backend&tag=fastapi")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert [item["slug"] for item in data["items"]] == ["fastapi-practice"]


def test_public_search_paginates(client: TestClient, search_data: dict[str, dict]) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?page=2&page_size=1")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["page"] == 2
    assert data["page_size"] == 1
    assert data["total_pages"] == 3
    assert data["items"][0]["slug"] == "fastapi-practice"


def test_public_search_ignores_blank_keyword(
    client: TestClient, search_data: dict[str, dict]
) -> None:
    response = client.get(f"{PUBLIC_ARTICLES_URL}?keyword=%20%20")

    assert response.status_code == 200
    assert response.json()["total"] == 3


def test_public_search_unknown_taxonomy_returns_empty(
    client: TestClient, search_data: dict[str, dict]
) -> None:
    by_category = client.get(f"{PUBLIC_ARTICLES_URL}?category=missing")
    by_tag = client.get(f"{PUBLIC_ARTICLES_URL}?tag=missing")

    assert by_category.status_code == 200
    assert by_category.json()["total"] == 0
    assert by_tag.status_code == 200
    assert by_tag.json()["total"] == 0


def test_admin_search_matches_drafts_and_honors_status(
    client: TestClient, auth_headers: dict[str, str], search_data: dict[str, dict]
) -> None:
    response = client.get(
        f"{ADMIN_ARTICLES_URL}?keyword=FastAPI&status=draft", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert [item["slug"] for item in data["items"]] == ["langgraph-draft"]


def test_admin_search_filters_by_category_and_tag(
    client: TestClient, auth_headers: dict[str, str], search_data: dict[str, dict]
) -> None:
    response = client.get(
        f"{ADMIN_ARTICLES_URL}?category_id={search_data['ai']['id']}"
        f"&tag_id={search_data['langgraph']['id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert [item["slug"] for item in data["items"]] == [
        "langgraph-draft",
        "chinese-search",
        "langgraph-intro",
    ]


def test_admin_search_supports_keyword_and_pagination(
    client: TestClient, auth_headers: dict[str, str], search_data: dict[str, dict]
) -> None:
    response = client.get(
        f"{ADMIN_ARTICLES_URL}?keyword=Python&page=1&page_size=1", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["total_pages"] == 2
    assert data["items"][0]["slug"] == "fastapi-practice"
