"""Single-user password login.

Set APP_PASSWORD (and SECRET_KEY, used to sign the login cookie) to turn it on.
Without APP_PASSWORD the app is open, which is only allowed with the local SQLite database.
"""
import asyncio
import hmac
import os
import secrets
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from .db import DATABASE_URL

PASSWORD = os.environ.get("APP_PASSWORD") or None
SECRET_KEY = os.environ.get("SECRET_KEY") or None
IS_LOCAL = DATABASE_URL.startswith("sqlite")
SESSION_MAX_AGE = 90 * 24 * 3600  # stay logged in on the phone for 90 days

if not IS_LOCAL and not PASSWORD:
    raise RuntimeError("APP_PASSWORD must be set when using a hosted database")
if PASSWORD and not SECRET_KEY and not IS_LOCAL:
    raise RuntimeError("SECRET_KEY must be set together with APP_PASSWORD")
SECRET_KEY = SECRET_KEY or secrets.token_urlsafe(32)  # local only: logins last until restart
COOKIE_SECURE = not IS_LOCAL  # HTTPS-only cookie when hosted

STATIC = Path(__file__).resolve().parent / "static"
PUBLIC_PATHS = {"/login", "/healthz", "/static/style.css", "/favicon.ico"}

router = APIRouter()


async def require_login(request: Request, call_next):
    if PASSWORD is None or request.url.path in PUBLIC_PATHS or request.session.get("auth"):
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not logged in"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


@router.get("/login", include_in_schema=False)
def login_page(request: Request):
    if PASSWORD is None or request.session.get("auth"):
        return RedirectResponse("/", status_code=303)
    return FileResponse(STATIC / "login.html")


@router.post("/login", include_in_schema=False)
async def login(request: Request):
    form = parse_qs((await request.body()).decode())
    given = (form.get("password") or [""])[0]
    if PASSWORD is not None and hmac.compare_digest(given.encode(), PASSWORD.encode()):
        request.session["auth"] = True
        return RedirectResponse("/", status_code=303)
    await asyncio.sleep(1)  # slow down password guessing
    return RedirectResponse("/login?error=1", status_code=303)


@router.post("/logout", include_in_schema=False)
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login" if PASSWORD else "/", status_code=303)
