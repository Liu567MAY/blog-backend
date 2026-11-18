from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.articles.models import Article, ArticleStatus

ADMIN_LIST_URL = "/api/v1/admin/articles"
PUBLIC_LIST_URL = "/api/v1/articles"


def _article(
    *,
    title: str,
    slug: str,
    status: ArticleStatus,
    created_at: datetime,
    published_at: datetime | None = None,
    content_markdown: str = "# 正文",
    summary: str | None = None,
) -> Article:
    return Article(
        title=title,
        slug=slug,
        summary=summary,
        content_markdown=content_markdown,
        status=status,
        created_at=created_at,
        updated_at=created_at,
        published_at=published_at,
    )


@pytest.fixture
def seeded_articles(db_session: Session) -> dict[str, Article]:
    articles = [
        _article(
            title="Published A",
            slug="published-a",
            status=ArticleStatus.PUBLISHED,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            content_markdown="# A",
            summary="A summary",
        ),
        _article(
            title="Published B",
            slug="published-b",
            status=ArticleStatus.PUBLISHED,
            created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
            published_at=datetime(2026, 1, 4, tzinfo=timezone.utc),
            content_markdown="# B",
        ),
        _article(
            title="Draft C",
            slug="draft-c",
            status=ArticleStatus.DRAFT,
            created_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
            content_markdown="# C draft",
        ),
    ]
    db_session.add_all(articles)
    db_session.commit()
    return {article.slug: article for article in articles}


def test_admin_list_requires_auth(client: TestClient) -> None:
    assert client.get(ADMIN_LIST_URL).status_code == 401


def test_admin_detail_requires_auth(
    client: TestClient, seeded_articles: dict[str, Article]
) -> None:
    article_id = seeded_articles["draft-c"].id
    assert client.get(f"{ADMIN_LIST_URL}/{article_id}").status_code == 401


def test_admin_list_returns_all_statuses_newest_first(
    client: TestClient, auth_headers: dict[str, str], seeded_articles: dict[str, Article]
) -> None:
    response = client.get(ADMIN_LIST_URL, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert [item["slug"] for item in data["items"]] == ["draft-c", "published-b", "published-a"]
    assert [item["status"] for item in data["items"]] == ["draft", "published", "published"]
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total_pages"] == 1


def test_admin_list_omits_markdown_content(
    client: TestClient, auth_headers: dict[str, str], seeded_articles: dict[str, Article]
) -> None:
    response = client.get(ADMIN_LIST_URL, headers=auth_headers)

    assert all("content_markdown" not in item for item in response.json()["items"])


def test_admin_list_filters_by_status(
    client: TestClient, auth_headers: dict[str, str], seeded_articles: dict[str, Article]
) -> None:
    response = client.get(f"{ADMIN_LIST_URL}?status=draft", headers=auth_headers)

    data = response.json()
    assert data["total"] == 1
    assert [item["slug"] for item in data["items"]] == ["draft-c"]


def test_admin_list_paginates(
    client: TestClient, auth_headers: dict[str, str], seeded_articles: dict[str, Article]
) -> None:
    response = client.get(f"{ADMIN_LIST_URL}?page=2&page_size=2", headers=auth_headers)

    data = response.json()
    assert [item["slug"] for item in data["items"]] == ["published-a"]
    assert data["total"] == 3
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert data["total_pages"] == 2


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=101", "status=archived"])
def test_admin_list_rejects_invalid_query(
    client: TestClient,
    auth_headers: dict[str, str],
    seeded_articles: dict[str, Article],
    query: str,
) -> None:
    response = client.get(f"{ADMIN_LIST_URL}?{query}", headers=auth_headers)
    assert response.status_code == 422


def test_admin_detail_returns_full_article_including_draft(
    client: TestClient, auth_headers: dict[str, str], seeded_articles: dict[str, Article]
) -> None:
    article = seeded_articles["draft-c"]
    response = client.get(f"{ADMIN_LIST_URL}/{article.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == article.id
    assert data["status"] == "draft"
    assert data["content_markdown"] == "# C draft"
    assert data["published_at"] is None


def test_admin_detail_missing_article_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"{ADMIN_LIST_URL}/999999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "文章不存在"


def test_public_list_returns_only_published_ordered_by_published_at(
    client: TestClient, seeded_articles: dict[str, Article]
) -> None:
    response = client.get(PUBLIC_LIST_URL)

    assert response.status_code == 200
    data = response.json()
    assert [item["slug"] for item in data["items"]] == ["published-b", "published-a"]
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 10


def test_public_list_omits_markdown_content(
    client: TestClient, seeded_articles: dict[str, Article]
) -> None:
    response = client.get(PUBLIC_LIST_URL)

    assert all("content_markdown" not in item for item in response.json()["items"])


def test_public_list_paginates(client: TestClient, seeded_articles: dict[str, Article]) -> None:
    response = client.get(f"{PUBLIC_LIST_URL}?page=2&page_size=1")

    data = response.json()
    assert [item["slug"] for item in data["items"]] == ["published-a"]
    assert data["total"] == 2
    assert data["total_pages"] == 2


def test_public_detail_returns_published_article_by_slug(
    client: TestClient, seeded_articles: dict[str, Article]
) -> None:
    response = client.get(f"{PUBLIC_LIST_URL}/published-b")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "published-b"
    assert data["title"] == "Published B"
    assert data["content_markdown"] == "# B"
    assert data["published_at"] is not None


@pytest.mark.parametrize("slug", ["draft-c", "does-not-exist"])
def test_public_detail_hides_drafts_and_missing_articles(
    client: TestClient, seeded_articles: dict[str, Article], slug: str
) -> None:
    response = client.get(f"{PUBLIC_LIST_URL}/{slug}")

    assert response.status_code == 404
    assert response.json()["detail"] == "文章不存在"


def test_public_list_rejects_out_of_range_page_size(
    client: TestClient, seeded_articles: dict[str, Article]
) -> None:
    assert client.get(f"{PUBLIC_LIST_URL}?page_size=101").status_code == 422
