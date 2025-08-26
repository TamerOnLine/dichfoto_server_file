from __future__ import annotations
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routers import public, likes, admin

def _load_settings():
    from app.core.config import get_settings
    return get_settings()

settings = _load_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(getattr(settings, "STATIC_DIR", "app/web/static")).mkdir(parents=True, exist_ok=True)
    Path(getattr(settings, "TEMPLATES_DIR", "app/web/templates")).mkdir(parents=True, exist_ok=True)
    yield

def create_app() -> FastAPI:
    app = FastAPI(
        title=getattr(settings, "PROJECT_NAME", "App"),
        debug=getattr(settings, "DEBUG", False),
        lifespan=lifespan,
        docs_url="/docs" if getattr(settings, "DEBUG", False) else None,
        redoc_url="/redoc" if getattr(settings, "DEBUG", False) else None,
        openapi_url=f"{getattr(settings, 'API_PREFIX', '/api')}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=getattr(settings, "ALLOWED_ORIGINS", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    if getattr(settings, "ENABLE_SESSIONS", True):
        secret = getattr(settings, "SECRET_KEY", "change-me")
        cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
        app.add_middleware(SessionMiddleware, secret_key=secret, session_cookie=cookie_name)

    trusted = getattr(settings, "TRUSTED_HOSTS", None)
    if trusted and trusted != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted)

    static_dir = getattr(settings, "STATIC_DIR", "app/web/static")
    templates_dir = getattr(settings, "TEMPLATES_DIR", "app/web/templates")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    templates = Jinja2Templates(directory=templates_dir)
    templates.env.globals["settings"] = settings

    api_prefix = getattr(settings, "API_PREFIX", "/api")
    app.include_router(public.router, prefix=api_prefix, tags=["public"])
    app.include_router(likes.router, prefix=api_prefix, tags=["likes"])
    app.include_router(admin.router, prefix=api_prefix, tags=["admin"])

    @app.get("/healthz", include_in_schema=False)
    def healthz_get() -> JSONResponse:
        return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})

    @app.head("/healthz", include_in_schema=False)
    def healthz_head() -> Response:
        return Response(status_code=200, headers={"Cache-Control": "no-store"})

    @app.get("/", include_in_schema=False)
    async def root(request: Request):
        index_html = Path(templates_dir) / "index.html"
        if index_html.exists():
            return templates.TemplateResponse("index.html", {"request": request})
        return HTMLResponse("<h1>Server running</h1>")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if str(request.url.path).startswith(api_prefix):
            return JSONResponse({"detail": exc.detail, "status_code": exc.status_code}, status_code=exc.status_code)
        return HTMLResponse(f"<h3>{exc.status_code}</h3><p>{exc.detail}</p>", status_code=exc.status_code)

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.server:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")), reload=True)
