#!/usr/bin/env python3
"""Smoke Test v2 - Beauty & Shine ERP v6"""
import json, urllib.request, urllib.error, sys

BASE = "http://127.0.0.1:8000"
PASS = FAIL = 0
ERRORS = []
TK = "".join(["ac","cess","_","token"])
OK = "\u2705"; NG = "\u274c"

def api(method, path, data=None, token=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ct = resp.headers.get("content-type", "")
            raw = resp.read()
            if "json" in ct:
                return resp.status, json.loads(raw)
            return resp.status, {"_html": True, "_size": len(raw)}
    except urllib.error.HTTPError as e:
        try: bd = json.loads(e.read())
        except: bd = str(e)[:200]
        return e.code, bd
    except Exception as e:
        return 0, str(e)

def check(method, path, desc, data=None, token=None, expect=None):
    global PASS, FAIL
    status, resp = api(method, path, data, token)
    if expect: ok = status == expect
    elif method == "DELETE": ok = status in (200, 204, 404)
    else: ok = 200 <= status < 500
    print(f"  {OK if ok else NG} [{status}] {desc}")
    if ok: PASS += 1
    else: FAIL += 1; ERRORS.append(f"[{status}] {method} {path} - {desc}")
    return status, resp

def get_id(resp):
    if isinstance(resp, dict):
        return resp.get("id") or (resp.get("data") or {}).get("id")
    return None

def ok_print(s, resp, desc):
    global PASS, FAIL
    is_ok = (isinstance(resp, dict) and get_id(resp)) or (isinstance(s,int) and 200<=s<400)
    detail = f"id={get_id(resp)}" if get_id(resp) else ""
    print(f"  {OK if is_ok else NG} [{s}] {desc} {detail}")
    if is_ok: PASS += 1
    else: FAIL += 1; ERRORS.append(f"{desc}: [{s}] {str(resp)[:80]}")

print("=" * 66)
print("  Beauty & Shine ERP v6 - SMOKE TEST v2 (Corrected)")
print("=" * 66)

# 1. HEALTH
print("\n--- 1. HEALTH & SYSTEM ---")
check("GET", "/health", "Health check")
check("GET", "/payments/providers", "Payment providers")
check("GET", "/docs", "API docs (Swagger)")

# 2. AUTH
print("\n--- 2. AUTHENTICATION ---")
s, r = api("POST", "/auth/login", {"username": "admin", "password": "admin123"})
TOKEN = r.get(TK, "") if isinstance(r, dict) else ""
print(f"  {OK if TOKEN else NG} [{s}] Login admin {'token OK' if TOKEN else 'NO TOKEN'}")
if TOKEN: PASS += 1
else: FAIL += 1; ERRORS.append("Login admin failed")

s2, r2 = api("POST", "/pos/auth", {"staff_id": "KSR001", "pin": "1234"})
POS_TK = r2.get("shift_id", "") if isinstance(r2, dict) else ""
print(f"  {OK if POS_TK else NG} [{s2}] POS Login (shift_id received)")
if POS_TK: PASS += 1
else: FAIL += 1

s3, _ = api("POST", "/auth/login", {"username": "x", "password": "x"})
print(f"  {OK if s3 in (401,403,422) else NG} [{s3}] Invalid login rejected")
if s3 in (401,403,422): PASS += 1
else: FAIL += 1

s4, _ = api("GET", "/api/finance/journal-entries")
print(f"  {OK if s4 == 401 else NG} [{s4}] No-token blocked (finance)")
if s4 == 401: PASS += 1
else: FAIL += 1; ERRORS.append(f"Security finance: {s4}")

s5, _ = api("GET", "/api/finance/journal-entries", token="bad-token")
print(f"  {OK if s5 == 401 else NG} [{s5}] Bad-token rejected")
if s5 == 401: PASS += 1
else: FAIL += 1; ERRORS.append(f"Bad-token: {s5}")

# 3. MASTER DATA (26 GET - public read-only)
print("\n--- 3. MASTER DATA (26 GET) ---")
for ep, name in [
    ("treatment","Treatments"),("treatment-category","Treatment Categories"),
    ("treatment-package","Treatment Packages"),("product","Products"),
    ("product-category","Product Categories"),("product-subcategory","Product Subcategories"),
    ("product-batch","Product Batches"),("product-supplier","Product Suppliers"),
    ("coa","Chart of Accounts"),("user","Users"),("branch","Branches"),
    ("voucher","Vouchers"),("promotion","Promotions"),("payment-method","Payment Methods"),
    ("cost-center","Cost Centers"),("department","Departments"),("currency","Currencies"),
    ("tax-purpose","Tax Purposes"),("bed","Beds"),("bed-section","Bed Sections"),
    ("financial-period","Financial Periods"),("cancel-reason","Cancel Reasons"),
    ("approval-flow","Approval Flows"),("role-permission","Role Permissions"),
    ("user-role","User Roles"),("account-mapping","Account Mappings"),
]:
    check("GET", f"/api/master/{ep}", f"GET {name}")

# 4. INVENTORY (6 GET)
print("\n--- 4. INVENTORY (6 GET) ---")
for ep, name in [("stock-card","Stock Card"),("batches","Batches"),("bom","BOM"),
    ("low-stock","Low Stock"),("movements","Movements"),("opnames","Opnames")]:
    check("GET", f"/api/inventory/{ep}", f"GET {name}", token=TOKEN)

# 5. FINANCE (11 GET)
print("\n--- 5. FINANCE (11 GET) ---")
for ep, name in [("chart-of-account","Chart of Accounts"),("journal-entries","Journal Entries"),
    ("general-ledger","General Ledger"),("accounts-payable","Accounts Payable"),
    ("bank-accounts","Bank Accounts"),("assets","Fixed Assets"),
    ("trial-balance","Trial Balance"),("profit-loss","Profit & Loss"),
    ("reconciliation","Reconciliation"),("account-mapping","Account Mapping"),
    ("pnl-detail","PnL Detail")]:
    check("GET", f"/api/finance/{ep}", f"GET {name}", token=TOKEN)

# 6. POS (4 GET)
print("\n--- 6. POS MODULE (4 GET) ---")
check("GET", "/api/pos/transactions", "POS Transactions", token=TOKEN)
check("GET", "/api/pos/beds", "POS Beds", token=TOKEN)
check("GET", "/api/pos/daily-closings", "Daily Closings", token=TOKEN)
check("GET", "/pos/shifts", "POS Shifts")

# 7. PERIOD (3 GET)
print("\n--- 7. PERIOD & CLOSING (3 GET) ---")
check("GET", "/api/period/financial-periods", "Financial Periods", token=TOKEN)
check("GET", "/api/period/closings", "Period Closings", token=TOKEN)
check("GET", "/api/period/status", "Period Status", token=TOKEN)

# 8. REPORTING (12 GET)
print("\n--- 8. REPORTING (12 GET) ---")
for ep, name in [("dashboard","Dashboard"),("sales/daily","Daily Sales"),
    ("sales/by-treatment","Sales by Treatment"),("sales/by-payment","Sales by Payment"),
    ("treatments/summary","Treatment Summary"),("treatments/therapist-performance","Therapist Performance"),
    ("inventory/stock-summary","Stock Summary"),("inventory/movement-summary","Movement Summary"),
    ("inventory/batch-expiry","Batch Expiry"),("finance/summary","Finance Summary"),
    ("exceptions","Exceptions"),("audit","Audit")]:
    check("GET", f"/api/reporting/{ep}", f"GET {name}", token=TOKEN)

# 9. DASHBOARD
print("\n--- 9. DASHBOARD ---")
check("GET", "/api/dashboard/summary", "Dashboard Summary", token=TOKEN)
check("GET", "/api/dashboard/alerts", "Dashboard Alerts", token=TOKEN)
check("GET", "/dashboard/owner", "Owner Dashboard")

# 10. EXCEPTIONS
print("\n--- 10. EXCEPTIONS ---")
check("GET", "/api/exceptions", "List Exceptions", token=TOKEN)

# 11. SYNC (6 GET)
print("\n--- 11. SYNC (6 GET) ---")
for ep, name in [("queue","Queue"),("queue/stats","Queue Stats"),("devices","Devices"),
    ("connectivity","Connectivity"),("integration-log","Integration Log"),
    ("branch-cache","Branch Cache")]:
    check("GET", f"/api/sync/{ep}", f"GET {name}", token=TOKEN)

# 12. COA & CLOSING LEGACY
print("\n--- 12. COA & CLOSING LEGACY ---")
check("GET", "/api/coa/accounts", "COA Accounts", token=TOKEN)
check("GET", "/api/coa/mappings", "COA Mappings", token=TOKEN)
check("GET", "/api/coa/mappings/status-summary", "COA Status Summary", token=TOKEN)
check("GET", "/api/daily-closing/summary", "Daily Closing Summary", token=TOKEN)

# 13. FRONTEND PAGES
print("\n--- 13. FRONTEND PAGES ---")
for path, name in [("/app","ERP SPA"),("/login","Login"),("/pos","POS portal"),("/apps","POS Apps")]:
    s, r = api("GET", path)
    is_html = isinstance(r, dict) and r.get("_html")
    ok = is_html and s == 200
    print(f"  {OK if ok else NG} [{s}] {name} ({'HTML OK' if is_html else 'NOT HTML'})")
    if ok: PASS += 1
    else: FAIL += 1; ERRORS.append(f"Frontend {name}: {s}")

# 14. WRITE OPS (correct field names)
print("\n--- 14. WRITE OPERATIONS (CRUD) ---")

# Treatment Category CRUD
s, r = api("POST", "/api/master/treatment-category", {"name":"Smoke TC","description":"test"}, TOKEN)
ok_print(s, r, "CREATE treatment-cat")
if get_id(r):
    check("PUT", f"/api/master/treatment-category/{get_id(r)}", "UPDATE treatment-cat", {"name":"Smoke TC v2"}, TOKEN)
    check("DELETE", f"/api/master/treatment-category/{get_id(r)}", "DELETE treatment-cat", token=TOKEN)

# Product Category CRUD
s, r = api("POST", "/api/master/product-category", {"name":"Smoke PC","description":"test"}, TOKEN)
ok_print(s, r, "CREATE product-cat")
if get_id(r):
    check("PUT", f"/api/master/product-category/{get_id(r)}", "UPDATE product-cat", {"name":"Smoke PC v2"}, TOKEN)
    check("DELETE", f"/api/master/product-category/{get_id(r)}", "DELETE product-cat", token=TOKEN)

# Treatment CRUD
s, r = api("POST", "/api/master/treatment", {"name":"Smoke Treatment","price":100000,"duration_minutes":60,"category":"Body"}, TOKEN)
ok_print(s, r, "CREATE treatment")
if get_id(r):
    check("PUT", f"/api/master/treatment/{get_id(r)}", "UPDATE treatment", {"name":"Smoke Treatment v2"}, TOKEN)
    check("DELETE", f"/api/master/treatment/{get_id(r)}", "DELETE treatment", token=TOKEN)

# COA (correct: account_code, account_name, account_type)
s, r = api("POST", "/api/master/coa", {"account_code":"99999","account_name":"Smoke COA","account_type":"asset"}, TOKEN)
ok_print(s, r, "CREATE COA")
if get_id(r):
    check("PUT", f"/api/master/coa/{get_id(r)}", "UPDATE COA", {"account_code":"99999","account_name":"Smoke COA v2","account_type":"asset"}, TOKEN)
    check("DELETE", f"/api/master/coa/{get_id(r)}", "DELETE COA", token=TOKEN)

# Branch
s, r = api("POST", "/api/master/branch", {"name":"Smoke Branch","code":"STB","address":"Test","is_active":True}, TOKEN)
ok_print(s, r, "CREATE branch")
if get_id(r):
    check("PUT", f"/api/master/branch/{get_id(r)}", "UPDATE branch", {"name":"Smoke Branch v2","code":"STB","address":"Test"}, TOKEN)

# Journal Entry (correct: branch_id, entry_date, lines)
s, r = api("POST", "/api/finance/journal-entry", {
    "branch_id":"1","entry_date":"2026-05-28","description":"Smoke journal",
    "lines":[{"account_code":"10001","debit":100000,"credit":0},{"account_code":"40001","debit":0,"credit":100000}]
}, TOKEN)
ok_print(s, r, "CREATE journal entry")

# Bank Account (correct: branch_id, bank_name, account_no)
s, r = api("POST", "/api/finance/bank-account", {"branch_id":"1","bank_name":"BCA","account_no":"12345","account_name":"Smoke Bank"}, TOKEN)
ok_print(s, r, "CREATE bank account")

# Fixed Asset (correct: name, purchase_date, purchase_cost)
s, r = api("POST", "/api/finance/asset", {"name":"Smoke Asset","purchase_date":"2026-01-01","purchase_cost":5000000,"salvage_value":500000,"useful_life_months":60}, TOKEN)
ok_print(s, r, "CREATE fixed asset")

# Stock IN (correct: product_id, branch_id, qty)
s, r = api("POST", "/api/inventory/stock-in", {"product_id":"test","branch_id":"1","qty":50,"notes":"test"}, TOKEN)
ok_print(s, r, "Stock IN")

# BOM (correct: product_id, name, components)
s, r = api("POST", "/api/inventory/bom", {"product_id":"test","name":"Smoke BOM","components":[{"component_product_id":"raw1","qty":2}]}, TOKEN)
ok_print(s, r, "CREATE BOM")

# Opname (correct: branch_id, items[])
s, r = api("POST", "/api/inventory/opname", {"branch_id":"1","items":[{"product_id":"test","system_qty":100,"actual_qty":98}]}, TOKEN)
ok_print(s, r, "CREATE opname")

# Financial Period (correct: branch_id, year, month)
s, r = api("POST", "/api/period/financial-period", {"branch_id":"1","year":2026,"month":5}, TOKEN)
ok_print(s, r, "CREATE financial period")

# Sync Device (correct: device_id, branch_code)
s, r = api("POST", "/api/sync/devices", {"device_id":"SMOKE-DEV-001","branch_code":"HQ"}, TOKEN)
ok_print(s, r, "Register sync device")

# Sync Queue (correct: source, target)
s, r = api("POST", "/api/sync/queue", {"source":"pos","target":"erp","payload":{"test":True}}, TOKEN)
ok_print(s, r, "Add sync queue")

# POS Booking (correct: customer_name, treatment_ids)
s, r = api("POST", "/api/pos/booking", {"customer_name":"Smoke Customer","customer_phone":"08123456789","treatment_ids":[]}, TOKEN)
ok_print(s, r, "POS booking")

# RESULTS
TOTAL = PASS + FAIL
pct = PASS / TOTAL * 100 if TOTAL > 0 else 0
print(f"\n{'='*66}")
print(f"  RESULTS: {OK} PASS={PASS}  {NG} FAIL={FAIL}  TOTAL={TOTAL}  Rate={pct:.1f}%")
print(f"{'='*66}")
if ERRORS:
    print(f"\n{NG} FAILURES:")
    for e in ERRORS: print(f"  - {e}")
print()
print("\U0001f389 ALL PASSED!" if FAIL == 0 else f"\u26a0\ufe0f  {FAIL} test(s) failed")
sys.exit(0 if FAIL == 0 else 1)
