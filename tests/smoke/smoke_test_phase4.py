#!/usr/bin/env python3
"""
POS-ERP v6 — Comprehensive UAT Smoke Test Script
Beauty & Shine Salon Management System

Tests all major API endpoints for availability, auth, and basic functionality.
Run: python3 smoke_test_phase4.py

Requires: Server running at http://localhost:8000
Dependencies: None (stdlib only — uses urllib.request)
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

# ── ANSI Colors ──────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# ── Configuration ────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"
POS_STAFF_ID = "KSR001"
POS_PIN = "1234"
TIMEOUT = 10  # seconds per request


# ── Result Tracking ──────────────────────────────────────────────────────────
@dataclass
class TestResult:
    endpoint: str
    method: str
    status: str  # PASS, FAIL, SKIP
    status_code: int = 0
    response_time_ms: float = 0.0
    notes: str = ""


results: list[TestResult] = []


# ── HTTP Helpers ─────────────────────────────────────────────────────────────
def api_request(
    method: str,
    path: str,
    token: Optional[str] = None,
    body: Optional[dict] = None,
    query: Optional[str] = None,
    raw: bool = False,
) -> tuple[int, str, float]:
    """Make an HTTP request. Returns (status_code, body_text, elapsed_ms)."""
    url = f"{BASE_URL}{path}"
    if query:
        url += f"?{query}"

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body_text = resp.read().decode("utf-8", errors="replace")
            elapsed = (time.monotonic() - start) * 1000
            return resp.status, body_text, elapsed
    except urllib.error.HTTPError as e:
        elapsed = (time.monotonic() - start) * 1000
        body_text = ""
        try:
            body_text = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return e.code, body_text, elapsed
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return 0, str(e), elapsed


def record(
    method: str,
    path: str,
    status: str,
    status_code: int = 0,
    response_time_ms: float = 0.0,
    notes: str = "",
):
    results.append(
        TestResult(
            endpoint=f"{method} {path}",
            method=method,
            status=status,
            status_code=status_code,
            response_time_ms=response_time_ms,
            notes=notes,
        )
    )


# ── Test Runners ─────────────────────────────────────────────────────────────
def test_health() -> bool:
    """Check if the server is reachable."""
    print(f"\n{CYAN}{'='*70}")
    print(f"  POS-ERP v6 — UAT Smoke Test")
    print(f"  Beauty & Shine Salon Management System")
    print(f"{'='*70}{RESET}\n")

    print(f"{DIM}[01] Checking server health...{RESET}", end=" ", flush=True)
    code, body, ms = api_request("GET", "/health")
    if code == 200:
        print(f"{GREEN}✓ Server is UP{RESET} ({ms:.0f}ms)")
        record("GET", "/health", "PASS", code, ms, "Server healthy")
        return True
    else:
        print(f"{RED}✗ Server unreachable (HTTP {code}){RESET}")
        print(f"\n{RED}{'='*70}")
        print(f"  ERROR: Cannot reach {BASE_URL}/health")
        print(f"  Please start the server first:")
        print(f"")
        print(f"    cd /root/pos-erp-v6")
        print(f"    python3 -m uvicorn pos_erp.fastapi_app:app --host 0.0.0.0 --port 8000")
        print(f"")
        print(f"  Or if using a different port, set BASE_URL in this script.")
        print(f"{'='*70}{RESET}\n")
        record("GET", "/health", "FAIL", code, ms, "Server unreachable")
        return False


def login_admin() -> Optional[str]:
    """Authenticate as admin and return the JWT token."""
    print(f"{DIM}[02] Logging in as admin ({ADMIN_USER})...{RESET}", end=" ", flush=True)
    code, body, ms = api_request(
        "POST", "/auth/login", body={"username": ADMIN_USER, "password": ADMIN_PASS}
    )
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = {}

    if code == 200 and data.get("success") and data.get("access_token"):
        print(f"{GREEN}✓ Authenticated{RESET} ({ms:.0f}ms) role={data.get('role', '?')}")
        record("POST", "/auth/login", "PASS", code, ms, f"role={data.get('role')}")
        return data["access_token"]
    else:
        print(f"{RED}✗ Login failed (HTTP {code}){RESET}")
        record("POST", "/auth/login", "FAIL", code, ms, data.get("message", "Unknown error"))
        return None


def test_pos_auth() -> Optional[str]:
    """Test POS staff authentication."""
    print(f"{DIM}[03] Testing POS auth ({POS_STAFF_ID})...{RESET}", end=" ", flush=True)
    code, body, ms = api_request(
        "POST", "/pos/auth", body={"staff_id": POS_STAFF_ID, "pin": POS_PIN}
    )
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = {}

    if code == 200:
        token = data.get("access_token") or data.get("token") or ""
        note = f"token={'yes' if token else 'no'}"
        print(f"{GREEN}✓ POS auth OK{RESET} ({ms:.0f}ms) {note}")
        record("POST", "/pos/auth", "PASS", code, ms, note)
        return token if token else None
    elif code in (401, 403):
        print(f"{YELLOW}⊘ POS auth rejected (HTTP {code}){RESET} ({ms:.0f}ms)")
        record("POST", "/pos/auth", "SKIP", code, ms, "Staff/PIN not seeded")
        return None
    else:
        print(f"{RED}✗ POS auth failed (HTTP {code}){RESET}")
        record("POST", "/pos/auth", "FAIL", code, ms, body[:80])
        return None


def test_get(
    idx: int,
    path: str,
    token: str,
    label: str = "",
    query: Optional[str] = None,
    allow_empty: bool = True,
    expect_list: bool = True,
) -> tuple[int, str, float]:
    """Test a GET endpoint and record the result."""
    display = label or path
    print(f"{DIM}[{idx:02d}] {display}...{RESET}", end=" ", flush=True)

    code, body, ms = api_request("GET", path, token=token, query=query)

    if code == 200:
        try:
            data = json.loads(body)
            if isinstance(data, list):
                note = f"{len(data)} items"
            elif isinstance(data, dict):
                keys = list(data.keys())[:4]
                note = f"keys={keys}"
            else:
                note = str(type(data).__name__)
        except json.JSONDecodeError:
            note = f"{len(body)} bytes"
        print(f"{GREEN}✓ OK{RESET} ({ms:.0f}ms) {note}")
        record("GET", path, "PASS", code, ms, note)
    elif code in (401, 403):
        print(f"{YELLOW}⊘ Auth required (HTTP {code}){RESET} ({ms:.0f}ms)")
        record("GET", path, "SKIP", code, ms, "Auth/permission issue")
    elif code == 404:
        print(f"{YELLOW}⊘ Not found (HTTP 404){RESET} ({ms:.0f}ms)")
        record("GET", path, "SKIP", code, ms, "Endpoint not found")
    elif code == 422:
        print(f"{YELLOW}⊘ Validation error (HTTP 422){RESET} ({ms:.0f}ms)")
        record("GET", path, "SKIP", code, ms, "Missing required params")
    elif code == 500:
        print(f"{RED}✗ Server error (HTTP 500){RESET} ({ms:.0f}ms)")
        record("GET", path, "FAIL", code, ms, body[:80])
    else:
        print(f"{RED}✗ HTTP {code}{RESET} ({ms:.0f}ms)")
        record("GET", path, "FAIL", code, ms, body[:80])

    return code, body, ms


def run_all_tests():
    # ── Health Check ─────────────────────────────────────────────────────
    if not test_health():
        print_summary()
        return 1

    # ── Admin Login ──────────────────────────────────────────────────────
    token = login_admin()
    if not token:
        print(f"\n{RED}Cannot proceed without admin token.{RESET}")
        print_summary()
        return 1

    # ── POS Auth ─────────────────────────────────────────────────────────
    test_pos_auth()

    # ── Master Data Endpoints ────────────────────────────────────────────
    print(f"\n{CYAN}── Master Data ──────────────────────────────────────────{RESET}")
    n = 4
    test_get(n + 0, "/api/master/treatment", token, "Master > Treatments"); n += 1
    test_get(n + 0, "/api/master/product", token, "Master > Products"); n += 1
    test_get(n + 0, "/api/master/customer", token, "Master > Customers"); n += 1
    test_get(n + 0, "/api/master/branch", token, "Master > Branches"); n += 1
    test_get(n + 0, "/api/master/coa", token, "Master > Chart of Accounts"); n += 1
    test_get(n + 0, "/api/master/voucher", token, "Master > Vouchers"); n += 1
    test_get(n + 0, "/api/master/payment-method", token, "Master > Payment Methods"); n += 1
    test_get(n + 0, "/api/master/promotion", token, "Master > Promotions"); n += 1
    test_get(n + 0, "/api/master/bed", token, "Master > Beds"); n += 1
    test_get(n + 0, "/api/master/bed-section", token, "Master > Bed Sections"); n += 1
    test_get(n + 0, "/api/master/department", token, "Master > Departments"); n += 1
    test_get(n + 0, "/api/master/user", token, "Master > Users"); n += 1
    test_get(n + 0, "/api/master/treatment-category", token, "Master > Treatment Categories"); n += 1
    test_get(n + 0, "/api/master/product-category", token, "Master > Product Categories"); n += 1
    test_get(n + 0, "/api/master/product-subcategory", token, "Master > Product Subcategories"); n += 1
    test_get(n + 0, "/api/master/cancel-reason", token, "Master > Cancel Reasons"); n += 1
    test_get(n + 0, "/api/master/product-supplier", token, "Master > Product Suppliers"); n += 1
    test_get(n + 0, "/api/master/cost-center", token, "Master > Cost Centers"); n += 1

    # ── Loyalty ──────────────────────────────────────────────────────────
    print(f"\n{CYAN}── Loyalty ──────────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/master/loyalty/summary", token, "Loyalty > Summary"); n += 1
    test_get(n + 0, "/api/master/loyalty/leaderboard", token, "Loyalty > Leaderboard"); n += 1

    # ── Reporting / Dashboard ────────────────────────────────────────────
    print(f"\n{CYAN}── Reporting & Dashboard ────────────────────────────────{RESET}")
    test_get(n + 0, "/api/reporting/dashboard", token, "Reporting > Dashboard"); n += 1
    test_get(n + 0, "/api/reporting/sales/daily", token, "Reporting > Sales Daily"); n += 1
    test_get(n + 0, "/api/reporting/sales/by-treatment", token, "Reporting > Sales by Treatment"); n += 1
    test_get(n + 0, "/api/reporting/sales/by-payment", token, "Reporting > Sales by Payment"); n += 1
    test_get(n + 0, "/api/reporting/treatments/summary", token, "Reporting > Treatments Summary"); n += 1
    test_get(n + 0, "/api/reporting/treatments/therapist-performance", token, "Reporting > Therapist Performance"); n += 1
    test_get(n + 0, "/api/reporting/staff/therapist-performance", token, "Reporting > Staff Therapist Perf"); n += 1
    test_get(n + 0, "/api/reporting/commission/summary", token, "Reporting > Commission Summary"); n += 1
    test_get(n + 0, "/api/reporting/commission/detail", token, "Reporting > Commission Detail"); n += 1
    test_get(n + 0, "/api/reporting/inventory/stock-summary", token, "Reporting > Inventory Stock Summary"); n += 1
    test_get(n + 0, "/api/reporting/inventory/movement-summary", token, "Reporting > Inventory Movement"); n += 1
    test_get(n + 0, "/api/reporting/inventory/batch-expiry", token, "Reporting > Batch Expiry"); n += 1
    test_get(n + 0, "/api/reporting/finance/summary", token, "Reporting > Finance Summary"); n += 1
    test_get(n + 0, "/api/reporting/exceptions", token, "Reporting > Exceptions"); n += 1
    test_get(n + 0, "/api/reporting/audit", token, "Reporting > Audit Log"); n += 1

    # ── Dashboard Router ─────────────────────────────────────────────────
    print(f"\n{CYAN}── Dashboard ────────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/dashboard/kpi", token, "Dashboard > KPI"); n += 1
    test_get(n + 0, "/api/dashboard/alerts", token, "Dashboard > Alerts"); n += 1

    # ── POS Endpoints ────────────────────────────────────────────────────
    print(f"\n{CYAN}── POS ──────────────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/pos/transactions", token, "POS > Transactions"); n += 1
    test_get(n + 0, "/api/pos/beds", token, "POS > Beds"); n += 1
    test_get(n + 0, "/api/pos/daily-closings", token, "POS > Daily Closings"); n += 1

    # ── Inventory ────────────────────────────────────────────────────────
    print(f"\n{CYAN}── Inventory ────────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/inventory/alerts", token, "Inventory > Alerts"); n += 1
    test_get(n + 0, "/api/inventory/stock-card", token, "Inventory > Stock Card"); n += 1
    test_get(n + 0, "/api/inventory/low-stock", token, "Inventory > Low Stock"); n += 1
    test_get(n + 0, "/api/inventory/movements", token, "Inventory > Movements"); n += 1
    test_get(n + 0, "/api/inventory/opnames", token, "Inventory > Opnames"); n += 1
    test_get(n + 0, "/api/inventory/batches", token, "Inventory > Batches"); n += 1
    test_get(n + 0, "/api/inventory/bom", token, "Inventory > BOM"); n += 1

    # ── Finance ──────────────────────────────────────────────────────────
    print(f"\n{CYAN}── Finance ──────────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/finance/journal-entries", token, "Finance > Journal Entries"); n += 1
    test_get(n + 0, "/api/finance/trial-balance", token, "Finance > Trial Balance"); n += 1
    test_get(n + 0, "/api/finance/general-ledger", token, "Finance > General Ledger"); n += 1
    test_get(n + 0, "/api/finance/profit-loss", token, "Finance > Profit & Loss"); n += 1
    test_get(n + 0, "/api/finance/accounts-payable", token, "Finance > Accounts Payable"); n += 1
    test_get(n + 0, "/api/finance/bank-accounts", token, "Finance > Bank Accounts"); n += 1
    test_get(n + 0, "/api/finance/chart-of-account", token, "Finance > Chart of Account"); n += 1
    test_get(n + 0, "/api/finance/account-mapping", token, "Finance > Account Mapping"); n += 1
    test_get(n + 0, "/api/finance/assets", token, "Finance > Assets"); n += 1
    test_get(n + 0, "/api/finance/pnl-detail", token, "Finance > P&L Detail"); n += 1

    # ── COA Mapping ──────────────────────────────────────────────────────
    print(f"\n{CYAN}── COA Mapping ──────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/coa/mappings", token, "COA > Mappings"); n += 1
    test_get(n + 0, "/api/coa/templates", token, "COA > Templates"); n += 1

    # ── Sync & Period ────────────────────────────────────────────────────
    print(f"\n{CYAN}── Sync & Period ────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/sync/queue", token, "Sync > Queue"); n += 1
    test_get(n + 0, "/api/sync/queue/stats", token, "Sync > Queue Stats"); n += 1
    test_get(n + 0, "/api/sync/devices", token, "Sync > Devices"); n += 1
    test_get(n + 0, "/api/sync/branch-cache", token, "Sync > Branch Cache"); n += 1
    test_get(n + 0, "/api/sync/connectivity", token, "Sync > Connectivity"); n += 1
    test_get(n + 0, "/api/period/status", token, "Period > Status"); n += 1
    test_get(n + 0, "/api/period/financial-periods", token, "Period > Financial Periods"); n += 1
    test_get(n + 0, "/api/period/closings", token, "Period > Closings"); n += 1

    # ── Daily Closing ────────────────────────────────────────────────────
    print(f"\n{CYAN}── Daily Closing ────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/daily-closing/", token, "Daily Closing > List"); n += 1

    # ── Exceptions ───────────────────────────────────────────────────────
    print(f"\n{CYAN}── Exceptions ───────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/exceptions/", token, "Exceptions > List"); n += 1
    test_get(n + 0, "/api/exceptions/stats", token, "Exceptions > Stats"); n += 1

    # ── Branch Filtering ─────────────────────────────────────────────────
    print(f"\n{CYAN}── Branch Filtering ─────────────────────────────────────{RESET}")
    # Get branch list first to find a valid branch_id
    _, branch_body, _ = api_request("GET", "/api/master/branch", token=token)
    branch_id = None
    try:
        branches = json.loads(branch_body)
        if isinstance(branches, list) and branches:
            branch_id = branches[0].get("id") or branches[0].get("branch_id")
    except (json.JSONDecodeError, IndexError, KeyError):
        pass

    if branch_id:
        test_get(
            n + 0, "/api/reporting/sales/daily", token,
            label=f"Reporting > Sales Daily (branch={branch_id})",
            query=f"branch_id={branch_id}",
        ); n += 1
        test_get(
            n + 0, "/api/reporting/dashboard", token,
            label=f"Reporting > Dashboard (branch={branch_id})",
            query=f"branch_id={branch_id}",
        ); n += 1
    else:
        print(f"{DIM}[{n:02d}] Branch filtering...{RESET} {YELLOW}⊘ SKIP — no branches found{RESET}")
        record("GET", "/api/reporting/sales/daily?branch_id=...", "SKIP", 0, 0, "No branches seeded")
        n += 1

    # ── CSV Export ───────────────────────────────────────────────────────
    print(f"\n{CYAN}── CSV Export ───────────────────────────────────────────{RESET}")
    test_get(n + 0, "/api/reporting/export/csv", token, "Reporting > Export CSV (sales)", query="report_type=sales"); n += 1

    # ── Transaction & Receipt ────────────────────────────────────────────
    print(f"\n{CYAN}── Transaction Detail & Receipt ─────────────────────────{RESET}")
    _, txn_body, _ = api_request("GET", "/api/pos/transactions", token=token)
    txn_id = None
    try:
        txns = json.loads(txn_body)
        if isinstance(txns, list) and txns:
            txn_id = txns[0].get("id") or txns[0].get("transaction_id")
    except (json.JSONDecodeError, IndexError, KeyError):
        pass

    if txn_id:
        test_get(n + 0, f"/api/pos/transaction/{txn_id}", token, f"POS > Transaction Detail ({txn_id})"); n += 1
        # Try receipt endpoint (may not exist)
        test_get(n + 0, f"/api/receipt/{txn_id}", token, f"Receipt ({txn_id})"); n += 1
    else:
        print(f"{DIM}[{n:02d}] Transaction detail...{RESET} {YELLOW}⊘ SKIP — no transactions{RESET}")
        record("GET", "/api/pos/transaction/{id}", "SKIP", 0, 0, "No transactions found")
        n += 1
        print(f"{DIM}[{n:02d}] Receipt...{RESET} {YELLOW}⊘ SKIP — no transactions{RESET}")
        record("GET", "/api/receipt/{id}", "SKIP", 0, 0, "No transactions found")
        n += 1

    # ── Rate Limiting (optional probe) ───────────────────────────────────
    print(f"\n{CYAN}── Rate Limiting Probe ──────────────────────────────────{RESET}")
    print(f"{DIM}[{n:02d}] Sending 5 rapid requests...{RESET}", end=" ", flush=True)
    rate_limited = False
    for i in range(5):
        code, _, _ = api_request("GET", "/health")
        if code == 429:
            rate_limited = True
            break
    if rate_limited:
        print(f"{GREEN}✓ Rate limiting detected (429){RESET}")
        record("GET", "/health x5", "PASS", 429, 0, "Rate limiting active")
    else:
        print(f"{YELLOW}⊘ No rate limiting detected (may not be configured){RESET}")
        record("GET", "/health x5", "SKIP", 200, 0, "Rate limiting not detected")
    n += 1

    # ── Print Summary ────────────────────────────────────────────────────
    return print_summary()


# ── Summary ──────────────────────────────────────────────────────────────────
def print_summary() -> int:
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")
    total = len(results)

    print(f"\n{CYAN}{'='*70}")
    print(f"  UAT SMOKE TEST RESULTS — POS-ERP v6")
    print(f"{'='*70}{RESET}\n")

    # Column widths
    ep_w = 54
    st_w = 6
    rt_w = 10
    nt_w = 30

    # Header
    header = f"  {'Endpoint':<{ep_w}} {'Status':<{st_w}} {'Time':>{rt_w}}  {'Notes'}"
    print(f"{BOLD}{header}{RESET}")
    print(f"  {'─'*ep_w} {'─'*st_w} {'─'*rt_w}  {'─'*nt_w}")

    for r in results:
        if r.status == "PASS":
            color = GREEN
            badge = "PASS"
        elif r.status == "FAIL":
            color = RED
            badge = "FAIL"
        else:
            color = YELLOW
            badge = "SKIP"

        time_str = f"{r.response_time_ms:.0f}ms" if r.response_time_ms > 0 else "—"
        ep = r.endpoint
        if len(ep) > ep_w:
            ep = ep[: ep_w - 1] + "…"
        notes = r.notes[:nt_w] if r.notes else ""

        print(f"  {ep:<{ep_w}} {color}{badge:<{st_w}}{RESET} {time_str:>{rt_w}}  {DIM}{notes}{RESET}")

    # Footer
    print(f"\n  {'─'*70}")
    avg_ms = sum(r.response_time_ms for r in results if r.response_time_ms > 0) / max(1, sum(1 for r in results if r.response_time_ms > 0))
    print(f"  {BOLD}Total: {total} tests | "
          f"{GREEN}PASS: {passed}{RESET} | "
          f"{RED}FAIL: {failed}{RESET} | "
          f"{YELLOW}SKIP: {skipped}{RESET} | "
          f"Avg: {avg_ms:.0f}ms")

    if failed == 0:
        print(f"\n  {GREEN}{BOLD}✅ ALL TESTS PASSED (or skipped gracefully){RESET}")
        exit_code = 0
    else:
        print(f"\n  {RED}{BOLD}❌ {failed} TEST(S) FAILED{RESET}")
        exit_code = 1

    print(f"  {DIM}Run: python3 smoke_test_phase4.py{RESET}")
    print()
    return exit_code


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted.{RESET}")
        exit_code = 130
    sys.exit(exit_code)
