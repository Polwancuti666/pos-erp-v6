from __future__ import annotations

from pos_erp.routers.checkout_router import router as checkout_router
from pos_erp.routers.exception_router import router as exception_router
from pos_erp.routers.dashboard_router import router as dashboard_router
from pos_erp.routers.coa_router import router as coa_router
from pos_erp.routers.closing_router import router as closing_router

__all__ = [
    "checkout_router",
    "exception_router",
    "dashboard_router",
    "coa_router",
    "closing_router",
]
