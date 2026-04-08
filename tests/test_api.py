"""Unit tests for the FastAPI application endpoints.

Uses FastAPI's TestClient (backed by httpx) to test each endpoint with
known HTML fixtures, verify JSON response structure, CORS headers, and
error handling.
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from brightspace_extractor.api import app

FIXTURES = Path(__file__).parent

client = TestClient(app)


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_ok(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class TestCORS:
    def test_chrome_extension_origin_allowed(self) -> None:
        resp = client.options(
            "/api/classlist",
            headers={
                "Origin": "chrome-extension://abcdef1234567890",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert (
            resp.headers.get("access-control-allow-origin")
            == "chrome-extension://abcdef1234567890"
        )

    def test_moz_extension_origin_allowed(self) -> None:
        resp = client.options(
            "/api/classlist",
            headers={
                "Origin": "moz-extension://abcdef1234567890",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert (
            resp.headers.get("access-control-allow-origin")
            == "moz-extension://abcdef1234567890"
        )

    def test_random_origin_rejected(self) -> None:
        resp = client.options(
            "/api/classlist",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert "access-control-allow-origin" not in resp.headers


# ---------------------------------------------------------------------------
# Empty body → 422
# ---------------------------------------------------------------------------


class TestEmptyBody:
    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/classlist",
            "/api/assignments",
            "/api/groups",
            "/api/quizzes",
            "/api/rubrics",
            "/api/extract",
        ],
    )
    def test_empty_body_returns_422(self, endpoint: str) -> None:
        resp = client.post(endpoint, content=b"")
        assert resp.status_code == 422
        assert "detail" in resp.json()

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/classlist",
            "/api/assignments",
            "/api/groups",
            "/api/quizzes",
            "/api/rubrics",
            "/api/extract",
        ],
    )
    def test_whitespace_only_body_returns_422(self, endpoint: str) -> None:
        resp = client.post(endpoint, content=b"   \n  ")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Listing endpoints with fixtures
# ---------------------------------------------------------------------------


class TestClasslistEndpoint:
    def test_returns_json_array(self) -> None:
        resp = client.post("/api/classlist", content=_fixture("classlist-debug.html"))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 37

    def test_each_item_has_required_keys(self) -> None:
        resp = client.post("/api/classlist", content=_fixture("classlist-debug.html"))
        for item in resp.json():
            assert "name" in item
            assert "org_defined_id" in item
            assert "role" in item

    def test_known_student_present(self) -> None:
        resp = client.post("/api/classlist", content=_fixture("classlist-debug.html"))
        by_name = {r["name"]: r for r in resp.json()}
        assert "Anwar Laroub" in by_name
        assert by_name["Anwar Laroub"]["org_defined_id"] == "500908250"


class TestAssignmentsEndpoint:
    def test_returns_json_array(self) -> None:
        resp = client.post(
            "/api/assignments", content=_fixture("assignments-debug.html")
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 28

    def test_each_item_has_required_keys(self) -> None:
        resp = client.post(
            "/api/assignments", content=_fixture("assignments-debug.html")
        )
        for item in resp.json():
            assert "assignment_id" in item
            assert "name" in item


class TestGroupsEndpoint:
    def test_returns_json_array(self) -> None:
        resp = client.post("/api/groups", content=_fixture("groups-debug.html"))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # extract_groups iterates all categories; fixture has 5 categories × 8 groups = 40
        assert len(data) == 40

    def test_each_item_has_required_keys(self) -> None:
        resp = client.post("/api/groups", content=_fixture("groups-debug.html"))
        for item in resp.json():
            assert "group_name" in item
            assert "members" in item


class TestQuizzesEndpoint:
    def test_returns_json_array(self) -> None:
        resp = client.post("/api/quizzes", content=_fixture("quizzes-debug.html"))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 24

    def test_each_item_has_required_keys(self) -> None:
        resp = client.post("/api/quizzes", content=_fixture("quizzes-debug.html"))
        for item in resp.json():
            assert "quiz_id" in item
            assert "name" in item


class TestRubricsEndpoint:
    def test_returns_json_array(self) -> None:
        resp = client.post("/api/rubrics", content=_fixture("rubrics-debug.html"))
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 15

    def test_each_item_has_required_keys(self) -> None:
        resp = client.post("/api/rubrics", content=_fixture("rubrics-debug.html"))
        for item in resp.json():
            assert "rubric_id" in item
            assert "name" in item
            assert "type" in item
            assert "scoring_method" in item
            assert "status" in item


# ---------------------------------------------------------------------------
# Extract endpoint
# ---------------------------------------------------------------------------


class TestExtractEndpoint:
    def test_no_submissions_returns_404(self) -> None:
        # Send HTML that has no group submission rows
        resp = client.post("/api/extract", content=b"<html><body>empty</body></html>")
        assert resp.status_code == 404
        assert "No group submissions" in resp.json()["detail"]

    def test_invalid_format_returns_422(self) -> None:
        resp = client.post("/api/extract?format=xml", content=b"<html></html>")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Error response structure
# ---------------------------------------------------------------------------


class TestErrorResponseStructure:
    def test_422_has_detail_field(self) -> None:
        resp = client.post("/api/classlist", content=b"")
        body = resp.json()
        assert "detail" in body
        assert isinstance(body["detail"], str)

    def test_404_has_detail_field(self) -> None:
        resp = client.post("/api/extract", content=b"<html><body>no data</body></html>")
        body = resp.json()
        assert "detail" in body
        assert isinstance(body["detail"], str)
