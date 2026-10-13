"""Serving the built web app from the API: pages, files, caching, and the API untouched."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.web import add_security_headers, mount_web_app


@pytest.fixture
def client(tmp_path) -> TestClient:
    (tmp_path / "index.html").write_text("<!doctype html><title>LedgerLet</title>")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log(1)")
    app = FastAPI()

    @app.get("/api/v1/ping")
    def ping() -> dict[str, str]:
        return {"pong": "yes"}

    add_security_headers(app, https=True)
    mount_web_app(app, str(tmp_path))
    return TestClient(app)


def test_any_page_address_gets_the_web_app_never_cached(client) -> None:
    for path in ("/", "/tax/2026/q2", "/properties/abc/edit"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "<title>LedgerLet</title>" in resp.text
        assert resp.headers["cache-control"] == "no-cache"


def test_hashed_assets_are_cached_for_a_year(client) -> None:
    resp = client.get("/assets/index-abc123.js")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert client.get("/assets/missing.js").status_code == 404


def test_top_level_files_are_served_as_themselves(client) -> None:
    assert client.get("/favicon.svg").text == "<svg/>"


def test_the_api_is_untouched_and_unknown_api_paths_stay_json(client) -> None:
    assert client.get("/api/v1/ping").json() == {"pong": "yes"}
    resp = client.get("/api/v1/nothing-here")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Not Found"}


def test_no_file_outside_the_folder_can_be_read(client) -> None:
    resp = client.get("/..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code == 200
    assert "<title>LedgerLet</title>" in resp.text  # just the app


def test_security_headers_on_every_response(client) -> None:
    for path in ("/", "/api/v1/ping"):
        headers = client.get(path).headers
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert headers["strict-transport-security"].startswith("max-age=31536000")


def test_a_missing_build_fails_at_start_not_on_first_visit(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="index.html is missing"):
        mount_web_app(FastAPI(), str(tmp_path))


def test_head_requests_work_for_uptime_checks(client) -> None:
    assert client.head("/").status_code == 200
