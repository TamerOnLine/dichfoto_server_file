#!/usr/bin/env python3
"""
Create DichFoto-style app skeleton with minimal runnable stubs.
Run: python bootstrap_scaffold.py
"""

from pathlib import Path
import os
import stat

ROOT = Path.cwd()

FILES: dict[str, str] = {
    # ---- core ----
    "app/core/__init__.py": "",
    "app/core/config/__init__.py": """# Re-export a getter for settings
from .base import get_settings
""",
    "app/core/config/base.py": r'''from pydantic import BaseModel
import os

class Settings(BaseModel):
    PROJECT_NAME: str = "Dich Foto"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    ALLOWED_ORIGINS: list[str] = ["*"]
    TRUSTED_HOSTS: list[str] = ["*"]
    SESSION_COOKIE_NAME: str = "sessionid"
    ENABLE_SESSIONS: bool = True
    STATIC_DIR: str = "app/web/static"
    TEMPLATES_DIR: str = "app/web/templates"

def get_settings() -> "Settings":
    env = os.getenv("ENV", "local").lower()
    if env in {"server", "prod", "production"}:
        from .server import Settings as S
        return S()
    elif env in {"local", "dev", "development"}:
        from .local import Settings as S
        return S()
    return Settings()
''',
    "app/core/config/local.py": """from .base import Settings as Base\n\nclass Settings(Base):\n    DEBUG: bool = True\n""",
    "app/core/config/server.py": """from .base import Settings as Base\n\nclass Settings(Base):\n    DEBUG: bool = False\n    ALLOWED_ORIGINS: list[str] = [\"https://dichfoto.com\", \"https://upload.dichfoto.com\"]\n    TRUSTED_HOSTS: list[str] = [\"dichfoto.com\", \"upload.dichfoto.com\", \"localhost\"]\n""",
    "app/core/security.py": '"""Security utilities (JWT/CSRF) — TODO."""\n',
    "app/core/logging.py": '"""Centralized logging config — TODO."""\n',

    # ---- db ----
    "app/db/__init__.py": "",
    "app/db/base.py": """from sqlalchemy.orm import DeclarativeBase\n\nclass Base(DeclarativeBase):\n    pass\n""",
    "app/db/engine.py": r'''import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
''',
    "app/db/session.py": """from sqlalchemy.orm import sessionmaker\nfrom .engine import engine\n\nSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)\n\ndef get_db():\n    db = SessionLocal()\n    try:\n        yield db\n    finally:\n        db.close()\n""",

    # ---- models ----
    "app/models/__init__.py": "from .album import Album  # noqa: F401\n",
    "app/models/album.py": """from sqlalchemy import String, Integer\nfrom sqlalchemy.orm import Mapped, mapped_column\nfrom app.db.base import Base\n\nclass Album(Base):\n    __tablename__ = \"albums\"\n    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)\n    title: Mapped[str] = mapped_column(String(200), index=True)\n""",
    "app/models/asset.py": '"""Asset model — TODO."""\n',
    "app/models/share.py": '"""Share model — TODO."""\n',
    "app/models/like.py": '"""Like model — TODO."""\n',

    # ---- api ----
    "app/api/__init__.py": "",
    "app/api/deps.py": "from app.db.session import get_db  # re-export\n",
    "app/api/routers/__init__.py": "from . import public, admin, likes  # noqa: F401\n",
    "app/api/routers/public.py": """from fastapi import APIRouter, Depends\nfrom sqlalchemy.orm import Session\nfrom app.api.deps import get_db\nfrom app.models.album import Album\n\nrouter = APIRouter()\n\n@router.get(\"/ping\")\ndef ping():\n    return {\"pong\": True}\n\n@router.get(\"/albums\")\ndef list_albums(db: Session = Depends(get_db)):\n    return db.query(Album).all()\n""",
    "app/api/routers/admin.py": """from fastapi import APIRouter, Depends\nfrom sqlalchemy.orm import Session\nfrom app.api.deps import get_db\nfrom app.models.album import Album\n\nrouter = APIRouter()\n\n@router.post(\"/admin/albums\")\ndef create_album(title: str, db: Session = Depends(get_db)):\n    album = Album(title=title)\n    db.add(album)\n    db.commit()\n    db.refresh(album)\n    return album\n""",
    "app/api/routers/likes.py": """from fastapi import APIRouter\n\nrouter = APIRouter()\n\n@router.get(\"/likes/health\")\ndef likes_health():\n    return {\"ok\": True}\n""",

    # ---- services ----
    "app/services/__init__.py": "",
    "app/services/gdrive.py": '"""Google Drive service — TODO."""\n',
    "app/services/variants.py": '"""Image variants service — TODO."""\n',
    "app/services/thumbs.py": '"""Thumbnails service — TODO."""\n',
    "app/services/zips.py": '"""ZIP archiving service — TODO."""\n',

    # ---- selectors ----
    "app/selectors/__init__.py": "",
    "app/selectors/albums.py": '"""Read-only queries for albums — TODO."""\n',

    # ---- viewmodels ----
    "app/viewmodels/__init__.py": "",
    "app/viewmodels/albums.py": '"""AlbumVM/AssetVM — TODO."""\n',

    # ---- web ----
    "app/web/templates/index.html": """<!doctype html>\n<html lang=\"en\">\n<head>\n  <meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n  <title>{{ settings.PROJECT_NAME }}</title>\n</head>\n<body>\n  <h1>{{ settings.PROJECT_NAME }}</h1>\n  <p>API prefix: <code>{{ settings.API_PREFIX }}</code></p>\n  <p>Try: <a href=\"{{ settings.API_PREFIX }}/ping\">{{ settings.API_PREFIX }}/ping</a></p>\n</body>\n</html>\n""",
    "app/web/static/.gitkeep": "",

    # ---- server (app factory) ----
    "app/server.py": r'''from __future__ import annotations
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
''',

    # ---- scripts ----
    "scripts/create_admin.py": r'''#!/usr/bin/env python3
"""Quick admin creator — TODO: integrate with real User model."""
print("create_admin: implement me once User model exists.")
''',
}

def main():
    # Create directories
    for rel in list(FILES.keys()):
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)

    # Write files (don't overwrite non-empty existing files)
    for rel, content in FILES.items():
        path = ROOT / rel
        if path.exists():
            try:
                if path.read_text(encoding="utf-8").strip():
                    # keep user content if non-empty
                    continue
            except Exception:
                pass
        path.write_text(content, encoding="utf-8")

    # Make script executable
    script = ROOT / "scripts/create_admin.py"
    if script.exists():
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

    print("✅ Scaffold created.")
    print("Next steps:")
    print("  1) Initialize DB tables:")
    print("     python -c \"from app.db.engine import engine; from app.db.base import Base; import app.models  # noqa; Base.metadata.create_all(engine)\"")
    print("  2) Run dev server:")
    print("     ENV=local uvicorn app.server:app --reload")
    print("  3) Try: GET /api/ping  |  POST /api/admin/albums?title=Test")

if __name__ == "__main__":
    main()
