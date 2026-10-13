"""Serving the built web app from the API, so production is one service at one address.

- /assets/* are Vite's hashed files: their names change when their content does, so
  browsers may keep them for a year.
- Any other path that isn't the API gets index.html, and the web app's router shows
  the right page (so /tax/2026/q2 works when opened directly or refreshed). It's
  never cached, so a new release shows up on the next visit.
- Unknown /api/... paths stay JSON 404s: they're mistakes, not pages.

Every response also gets a few standard security headers.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
HSTS = "max-age=31536000; includeSubDomains"


def add_security_headers(app: FastAPI, *, https: bool) -> None:
    @app.middleware("http")
    async def _headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if https:
            response.headers.setdefault("Strict-Transport-Security", HSTS)
        return response


class _ImmutableFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def mount_web_app(app: FastAPI, static_dir: str) -> None:
    root = Path(static_dir).resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"No built web app at {root} (index.html is missing)")

    if (root / "assets").is_dir():
        app.mount("/assets", _ImmutableFiles(directory=root / "assets"), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def web_app(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        # A real file at the top level (favicon, robots.txt), never outside the folder.
        candidate = (root / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
