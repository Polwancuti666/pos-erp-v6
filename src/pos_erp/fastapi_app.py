from __future__ import annotations
import logging
import os
import re
import time
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pos_erp.beauty_ui import render_dashboard_html
from pos_erp.auth import router as auth_router, verify_access_token
from pos_erp.pos_auth import router as pos_auth_router
from pos_erp.routers import (
    checkout_router,
    exception_router,
    dashboard_router,
    coa_router,
    closing_router,
)
from pos_erp.routers.master_router import router as master_router
from pos_erp.routers.pos_router_v2 import router as pos_router
from pos_erp.routers.inventory_router_v2 import router as inventory_router
from pos_erp.routers.finance_router_v2 import router as finance_router
from pos_erp.routers.sync_router import router as sync_router
from pos_erp.routers.period_router import router as period_router
from pos_erp.routers.reporting_router import router as reporting_router
from pos_erp.routers.doc_registry_router import router as doc_registry_router
from pos_erp.routers.receipt_router import router as receipt_router
from pos_erp.routers.wip_router import router as wip_router
from pos_erp.routers.asset_router import router as asset_router
from pos_erp.routers.bank_recon_router import router as bank_recon_router
from pos_erp.routers.cost_center_router import router as cost_center_router
from pos_erp.routers.schedule_router import router as schedule_router
from pos_erp.routers.certification_router import router as certification_router
from pos_erp.routers.pricelist_router import router as pricelist_router
from pos_erp.routers.cancel_reason_router import router as cancel_reason_router
from pos_erp.routers.recurring_journal_router import router as recurring_journal_router
from pos_erp.routers.cash_flow_router import router as cash_flow_router
from pos_erp.routers.whatsapp_router import router as whatsapp_router
from pos_erp.routers.executive_router import router as executive_router
from pos_erp.routers.coa_upload_router import router as coa_upload_router
from pos_erp.routers.coa_management_router import router as coa_management_router
from pathlib import Path

logger = logging.getLogger("pos_erp.security")

# ── Security hardening constants ──────────────────────────────────
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "*").split(",")
    if o.strip()
]
MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MB
RATE_LIMIT_API = 100   # requests per minute for general API
RATE_LIMIT_AUTH = 10   # requests per minute for auth endpoints
RATE_WINDOW_SEC = 60    # 1-minute sliding window
SLOW_REQUEST_SEC = 2.0  # log requests slower than this


class _RateLimitStore:
    """Simple in-memory sliding-window rate limiter keyed by client IP."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window: float = RATE_WINDOW_SEC) -> bool:
        now = time.monotonic()
        bucket = self._hits[key]
        # Prune expired entries
        cutoff = now - window
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


_rate_store = _RateLimitStore()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach standard security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit by client IP.  Auth endpoints get a tighter budget."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Determine which bucket & limit applies
        if path.startswith("/api/auth") or path.startswith("/api/pos/auth"):
            limit = RATE_LIMIT_AUTH
            bucket_key = f"auth:{client_ip}"
        else:
            limit = RATE_LIMIT_API
            bucket_key = f"api:{client_ip}"

        if not _rate_store.is_allowed(bucket_key, limit):
            return JSONResponse(
                {"detail": "Rate limit exceeded. Try again later."},
                status_code=429,
            )
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds MAX_BODY_BYTES."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse(
                {"detail": "Request body too large (max 1 MB)"},
                status_code=413,
            )
        return await call_next(request)


class SlowRequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log a warning for requests that take longer than SLOW_REQUEST_SEC."""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start
        if elapsed > SLOW_REQUEST_SEC:
            logger.warning(
                "SLOW REQUEST %.2fs  %s %s  status=%s",
                elapsed,
                request.method,
                request.url.path,
                response.status_code,
            )
        return response

_INDEX_HTML = (Path(__file__).parent / "index.html").read_text()
_POS_HTML = (Path(__file__).parent / "pos_index.html").read_text()
_POS_LANDING_HTML = (Path(__file__).parent / "pos_landing.html").read_text()
_LOGIN_HTML = (Path(__file__).parent / "login.html").read_text()
_LANDING_HTML = (Path(__file__).parent / "landing.html").read_text()

# Frontend dist directory
_FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"

def create_app() -> FastAPI:
    app = FastAPI(title="POS-ERP Integration Engine V6", version="0.1.0")

    # ── CORS ──────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Security hardening middleware (outermost first) ────────────
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SlowRequestLoggingMiddleware)

    # ── Auth middleware for /api/* routes ──────────────────────────
    _SKIP_AUTH_PREFIXES = (
        "/health", "/docs", "/openapi.json", "/login",
        "/auth/", "/api/pos/auth", "/api/pos/shift",
        "/pos/auth", "/pos/shifts", "/pos",
        "/dashboard/", "/payments/", "/app/", "/assets/", "/apps",
        "/api/executive/summary", "/api/executive/branch-comparison",
        "/api/executive/top-treatments", "/api/executive/top-therapists",
        "/receipt/",  # receipt HTML/JSON public for printing
    )

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path
        # Skip auth for non-API paths
        if not path.startswith("/api/"):
            return await call_next(request)
        # Allow whitelisted prefixes without auth (login, shifts, etc.)
        for prefix in _SKIP_AUTH_PREFIXES:
            if path.startswith(f"/api{prefix}") or path.startswith(prefix):
                return await call_next(request)
        # Allow /api/master/* GET without auth (read-only catalog)
        if path.startswith("/api/master/") and request.method == "GET":
            return await call_next(request)
        # Allow /api/doc-registry/* GET without auth (read-only registry)
        if path.startswith("/api/doc-registry/") and request.method == "GET":
            return await call_next(request)
        # Check Bearer token for all other /api/* routes
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)
        token = auth_header[7:]
        payload = verify_access_token(token)
        if payload is None:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)
        return await call_next(request)

    # ── Existing routers ─────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(pos_auth_router, prefix="/api")

    # ── New module routers ───────────────────────────────────────────
    app.include_router(checkout_router)
    app.include_router(exception_router)
    app.include_router(dashboard_router)
    app.include_router(coa_router)
    app.include_router(closing_router)
    
    # ── BPMN v3 Module routers ──────────────────────────────────────
    app.include_router(master_router)
    app.include_router(pos_router)
    app.include_router(inventory_router)
    app.include_router(finance_router)
    app.include_router(sync_router)
    app.include_router(period_router)
    app.include_router(reporting_router)
    app.include_router(doc_registry_router)
    app.include_router(receipt_router)
    
    # ── Phase 4+ BPMN v3 Additional Modules ──────────────────
    app.include_router(wip_router)
    app.include_router(asset_router)
    app.include_router(bank_recon_router)
    app.include_router(cost_center_router)
    app.include_router(schedule_router)
    app.include_router(certification_router)
    app.include_router(pricelist_router)
    app.include_router(cancel_reason_router)
    
    # ── Phase 4B Remaining BPMN v3 Modules ───────────────────
    app.include_router(recurring_journal_router)
    app.include_router(cash_flow_router)
    app.include_router(whatsapp_router)
    app.include_router(executive_router)
    app.include_router(coa_upload_router)
    app.include_router(coa_management_router)
    
    @app.get("/")
    def root(request: Request):
        host = request.headers.get("host", "")
        # beautynshine.web.id → landing page
        if host == "beautynshine.web.id" or host == "www.beautynshine.web.id":
            return HTMLResponse(_LANDING_HTML)
        # erp.beautynshine.web.id → login page
        if "erp." in host:
            return HTMLResponse(_LOGIN_HTML)
        # pos.beautynshine.web.id → POS landing
        if "pos." in host:
            return RedirectResponse(url="/pos", status_code=302)
        # beautynshine.com → landing page
        if "beautynshine.com" in host:
            return HTMLResponse(_LANDING_HTML)
        return HTMLResponse(_INDEX_HTML)

    @app.get("/login")
    def login_page() -> HTMLResponse:
        return HTMLResponse(_LOGIN_HTML)

    @app.get("/pos", response_class=HTMLResponse)
    @app.get("/pos/{path:path}", response_class=HTMLResponse)
    async def serve_pos_app(path: str = ""):
        """Serve POS SPA on the main Cloudflare-protected domain.

        This keeps the public portal on beautynshine.web.id from sending users
        to pos.beautynshine.web.id, which may be accessed directly and show the
        origin self-signed certificate in browsers.
        """
        return FileResponse(str(_FRONTEND_DIST / "pos.html"))
    
    # /apps removed — old POS landing
        
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "pos-erp-v6"}

    @app.get("/dashboard/owner")
    def owner_dashboard() -> dict[str, object]:
        return {"theme": {"industry": "beauty-wellbeing", "mood": "cute-premium"}, "cards": []}

    # /dashboard — Executive Dashboard with live API data
    _PORTAL_HTML = (Path(__file__).parent / "dashboard_executive.html").read_text()
    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard_portal() -> HTMLResponse:
        return HTMLResponse(content=_PORTAL_HTML, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

    @app.get("/payments/providers")
    def providers() -> dict[str, list[str]]:
        return {"providers": ["BCA", "MIDTRANS"]}

    # ── Serve React Frontend ────────────────────────────────────────
    if _FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIST / "assets")), name="static-assets")

        # SPA catch-all — serve correct HTML based on subdomain
        @app.get("/app/{path:path}")
        async def serve_spa(path: str, request: Request):
            """Serve React SPA — all /app/* routes return correct index for client-side routing."""
            file_path = _FRONTEND_DIST / path
            if file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            host = request.headers.get("host", "")
            # pos.beautynshine.web.id → POS app
            if "pos." in host:
                return FileResponse(str(_FRONTEND_DIST / "pos.html"))
            # Default → ERP app
            return FileResponse(str(_FRONTEND_DIST / "index.html"))

        @app.get("/app")
        async def serve_spa_root(request: Request):
            host = request.headers.get("host", "")
            # pos.beautynshine.web.id/app → POS app
            if "pos." in host:
                return FileResponse(str(_FRONTEND_DIST / "pos.html"))
            # erp.beautynshine.web.id/app → ERP app
            return FileResponse(str(_FRONTEND_DIST / "index.html"))

    return app

app = create_app()
