from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pos_erp.beauty_ui import render_dashboard_html
from pos_erp.auth import router as auth_router
from pos_erp.pos_auth import router as pos_auth_router
from pos_erp.routers import (
    checkout_router,
    exception_router,
    dashboard_router,
    coa_router,
    closing_router,
)
from pathlib import Path

_INDEX_HTML = (Path(__file__).parent / "index.html").read_text()
_POS_HTML = (Path(__file__).parent / "pos_index.html").read_text()
_LOGIN_HTML = (Path(__file__).parent / "login.html").read_text()

def create_app() -> FastAPI:
    app = FastAPI(title="POS-ERP Integration Engine V6", version="0.1.0")

    # ── Existing routers ─────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(pos_auth_router)

    # ── New module routers ───────────────────────────────────────────
    app.include_router(checkout_router)
    app.include_router(exception_router)
    app.include_router(dashboard_router)
    app.include_router(coa_router)
    app.include_router(closing_router)
    
    @app.get("/")
    def root(request: Request) -> HTMLResponse:
        host = request.headers.get("host", "")
        if "pos." in host:
            return HTMLResponse(_POS_HTML)
        if "erp." in host:
            return HTMLResponse(_LOGIN_HTML)
        return HTMLResponse(_INDEX_HTML)

    @app.get("/login")
    def login_page() -> HTMLResponse:
        return HTMLResponse(_LOGIN_HTML)

    @app.get("/pos")
    def pos_portal() -> HTMLResponse:
        return HTMLResponse(_POS_HTML)
        
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "pos-erp-v6"}
    @app.get("/dashboard/owner")
    def owner_dashboard() -> dict[str, object]:
        return {"theme": {"industry": "beauty-wellbeing", "mood": "cute-premium"}, "cards": []}
    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard_html() -> str:
        return render_dashboard_html(branch_name="Beauty Wellbeing HQ")
    @app.get("/payments/providers")
    def providers() -> dict[str, list[str]]:
        return {"providers": ["BCA", "MIDTRANS"]}
    return app
app = create_app()
