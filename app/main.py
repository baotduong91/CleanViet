from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.config import settings
from app.db import engine, session_dependency
from app.routes.canvas import router


@asynccontextmanager
async def lifespan(app):
    yield
    await engine.dispose()


app = FastAPI(title="CleanViet Pantry Arbitrage", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts,
)
DB = Depends(session_dependency)


def _request_hostname(host_header: str | None) -> str | None:
    if not host_header:
        return None
    if host_header.startswith("["):
        end = host_header.find("]")
        return host_header[1:end] if end > 0 else host_header
    return host_header.rsplit(":", 1)[0]


def _write_origin_permitted(origin: str | None, host: str | None) -> bool:
    """Allow writes from trusted frontends (incl. Vite proxy on another port)."""
    trusted = set(settings.trusted_hosts)
    if not origin:
        return True
    parsed = urlparse(origin)
    if parsed.scheme not in ("http", "https"):
        return False
    origin_host = parsed.hostname
    if not origin_host or origin_host not in trusted:
        return False
    request_host = _request_hostname(host)
    if request_host and request_host not in trusted and request_host != origin_host:
        return False
    return True


@app.middleware("http")
async def browser_security(request: Request, call_next):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        host = request.headers.get("host")
        cross_site = request.headers.get("sec-fetch-site") == "cross-site"
        if cross_site:
            if not origin or not _write_origin_permitted(origin, host):
                return JSONResponse(
                    {"detail": "Cross-origin writes are not permitted."},
                    status_code=403,
                )
        elif origin and not _write_origin_permitted(origin, host):
            return JSONResponse(
                {"detail": "Cross-origin writes are not permitted."}, status_code=403
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    )
    if request.url.path in ("/docs", "/redoc"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; font-src data:; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
        )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    import logging

    logging.getLogger("cleanviet").exception("Database operation failed", exc_info=exc)
    return JSONResponse(
        {
            "detail": "Database unavailable or transaction failed. Retry after checking the local database."
        },
        status_code=503,
    )


@app.get("/api/health")
async def health(session: AsyncSession = DB):
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "planner": "Monday–Thursday canvas"}


app.include_router(router)

DISH_MEDIA = Path(__file__).resolve().parent.parent / "data" / "dish_images"
try:
    DISH_MEDIA.mkdir(parents=True, exist_ok=True)
except OSError:
    pass
if DISH_MEDIA.is_dir():
    app.mount("/media/dishes", StaticFiles(directory=DISH_MEDIA), name="dish_images")

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Unknown API endpoint.")
        candidate = (DIST / path).resolve()
        if candidate.is_relative_to(DIST.resolve()) and candidate.is_file():
            return FileResponse(
                candidate,
                headers={"Cache-Control": "no-cache"}
                if path in ("sw.js", "manifest.webmanifest", "index.html")
                else {},
            )
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
