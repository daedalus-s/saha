from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.extract import extract_from_url
from app.models import (
    ExtractRequest,
    ExtractResponse,
    SearchRequest,
    SearchResponse,
    TransliterateRequest,
    TransliterateResponse,
    TranslateRequest,
    TranslateResponse,
)
from app.search import search_sloka
from app.transliterate import SCHEME_BY_SCRIPT, transliterate_verses
from app.translate import translate_verses

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

OPEN_PATHS = {
    "/health",
    "/privacy",
    "/terms",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}


def _docs_dir() -> Path:
    if settings.docs_dir:
        return Path(settings.docs_dir)
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "docs",  # repo root when running from services/api/app
        here.parents[2] / "docs",
        Path("/app/docs"),
        Path.cwd() / "docs",
        Path.cwd().parent.parent / "docs",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return candidates[0]


def _markdown_file(name: str) -> str:
    path = _docs_dir() / name
    if not path.is_file():
        return f"# {name}\nDocument not found."
    return path.read_text(encoding="utf-8")


def _md_to_html(title: str, markdown: str) -> str:
    body = (
        markdown.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    # Very small markdown subset: headings and paragraphs
    lines = []
    for line in body.splitlines():
        if line.startswith("# "):
            lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            lines.append(f"<h3>{line[4:]}</h3>")
        elif line.strip() == "":
            lines.append("")
        elif line.startswith("- "):
            lines.append(f"<li>{line[2:]}</li>")
        else:
            lines.append(f"<p>{line}</p>")
    inner = "\n".join(lines)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    body {{ font-family: Georgia, serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #1a1a1a; }}
    h1, h2, h3 {{ font-family: system-ui, sans-serif; }}
    li {{ margin-left: 1.2rem; }}
  </style>
</head>
<body>
{inner}
</body>
</html>"""


app = FastAPI(title="Saha API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_app_key(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in OPEN_PATHS:
        return await call_next(request)
    key = request.headers.get("X-App-Key", "")
    expected = get_settings().app_key
    if not expected or key != expected:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "search_provider": settings.search_provider,
        "llm_enabled": settings.llm_enabled,
    }


@app.get("/privacy", response_class=HTMLResponse)
async def privacy():
    return _md_to_html("Privacy Policy — Saha", _markdown_file("privacy.md"))


@app.get("/terms", response_class=HTMLResponse)
async def terms():
    return _md_to_html("Terms of Use — Saha", _markdown_file("terms.md"))


@app.post("/search", response_model=SearchResponse)
@limiter.limit("20/minute")
async def search(request: Request, body: SearchRequest):
    try:
        return await search_sloka(body.query, script=body.script)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Search failed: {exc}") from exc


@app.post("/extract", response_model=ExtractResponse)
@limiter.limit("40/minute")
async def extract(request: Request, body: ExtractRequest):
    return await extract_from_url(str(body.url), query=body.query)


@app.post("/transliterate", response_model=TransliterateResponse)
@limiter.limit("60/minute")
async def transliterate(request: Request, body: TransliterateRequest):
    if body.source_script.lower() not in SCHEME_BY_SCRIPT:
        raise HTTPException(status_code=400, detail=f"Unsupported source script: {body.source_script}")
    if body.target_script.lower() not in SCHEME_BY_SCRIPT:
        raise HTTPException(status_code=400, detail=f"Unsupported target script: {body.target_script}")
    try:
        verses = transliterate_verses(body.verses, body.source_script, body.target_script)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TransliterateResponse(
        verses=verses,
        source_script=body.source_script,
        target_script=body.target_script,
    )


@app.post("/translate", response_model=TranslateResponse)
@limiter.limit("20/minute")
async def translate(request: Request, body: TranslateRequest):
    try:
        return await translate_verses(
            body.verses,
            source_script=body.source_script,
            target_language=body.target_language,
            title=body.title,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Translation failed: {exc}") from exc
