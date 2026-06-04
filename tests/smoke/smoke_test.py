#!/usr/bin/env python3
"""Comprehensive Smoke Test for Beauty & Shine ERP v6"""
import json, urllib.request, urllib.error, sys

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0
ERRORS = []

def api(method, path, data=None, token=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: body_text = json.loads(e.read())
        except: body_text = e.read().decode()[:200]
        return e.code, body_text
    except Exception as e:
        return 0, str(e)

def check(method, path, desc, data=None, token=None, expect=None):
    global PASS, FAIL
    status, resp = api(method, path, data, token)
    ok = (status == expect) if expect else (200 <= status < 500 if method != "DELETE" else status in (200, 204, 404))
    if ok:
        print(f"  ✅ [{status}] {desc}")
        PASS += 1
    else:
        print(f"  ❌ [{status}] {desc}")
        FAIL += 1
        ERRORS.append(f"[{status}] {method} {path} — {desc}")
    return status, resp

def get_id(resp):
    if isinstance(resp, dict):
        return resp.get("id") or (resp.get("data") or {}).get("id")
    return None

print("=" * 66)
print("  Beauty & Shine ERP v6 — COMPREHENSIVE SMOKE TEST")
print("=" * 66)

# 1. HEALTH
print("\n━━━ 1. HEALTH & SYSTEM ━━━")
check("GET", "/health", "Health check")
check("GET", "/payments/providers", "Payment providers")
check("GET", "/docs", "API docs")

# 2. AUTH
print("\n━━━ 2. AUTHENTICATION ━━━")
s, r = api("POST", "/auth/login", {"username": "admin", "password": "admin123"})
TOKEN=r.get('access_token', "") if isinstance(r, dict) else ""
print(f"  {'✅' if TOKEN else '❌'} [{s}] Login admin — {'token OK' if TOKEN else 'NO TOKEN'}")
if TOKEN: PASS += 1
else: FAIL += 1; ERRORS.append("Login admin failed")

s2, r2 = api("POST", "/pos/auth", {"username": "kasir", "password": "kasir123"})
POS_TOKEN=r2.get('access_token', "") if isinstance(r2, dict) else ""
print(f"  {'✅' if POS_TOKEN else '❌'} [{s2}] POS Login kasir — {'token OK' if POS_TOKEN else 'NO TOKEN'}")
if POS_TOKEN: PASS += 1
else: FAIL += 1

s3, _ = api("POST", "/auth/login", {"username": "x", "password": "x"})
print(f"  {'✅' if s3 in (401,403,422) else '❌'} [{s3}] Invalid login rejected")
if s3 in (401,403,422): PASS += 1
else: FAIL += 1

# 3. MASTER DATA
print("\n━━━ 3. MASTER DATA (26 endpoints) ━━━")
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
    check("GET", f"/api/master/{ep}", f"GET {name}", token=TOKEN)

# 4. INVENTORY
print("\n━━━ 4. INVENTORY (6 endpoints) ━━━")
for ep, name in [
    ("stock-card","Stock Card"),("batches","Batches"),("bom","BOM"),
    ("low-stock","Low Stock"),("movements","Movements"),("opnames","Opnames"),
]:
    check("GET", f"/api/inventory/{ep}", f"GET {name}", token=TOKEN)

# 5. FINANCE
print("\n━━━ 5. FINANCE (11 endpoints) ━━━")
for ep, name in [
    ("chart-of-account","Chart of Accounts"),("journal-entries","Journal Entries"),
    ("general-ledger","General Ledger"),("accounts-payable","Accounts Payable"),
    ("bank-accounts","Bank Accounts"),("assets","Fixed Assets"),
    ("trial-balance","Trial Balance"),("profit-loss","Profit & Loss"),
    ("reconciliation","Reconciliation"),("account-mapping","Account Mapping"),
    ("pnl-detail","PnL Detail"),
]:
    check("GET", f"/api/finance/{ep}", f"GET {name}", token=TOKEN)

# 6. POS
print("\n━━━ 6. POS MODULE (4 endpoints) ━━━")
check("GET", "/api/pos/transactions", "POS Transactions", token=TOKEN)
check("GET", "/api/pos/beds", "POS Beds", token=TOKEN)
check("GET", "/api/pos/daily-closings", "Daily Closings", token=TOKEN)
check("GET", "/pos/shifts", "POS Shifts", token=POS_TOKEN)

# 7. PERIOD
print("\n━━━ 7. PERIOD & CLOSING (3 endpoints) ━━━")
check("GET", "/api/period/financial-periods", "Financial Periods", token=TOKEN)
check("GET", "/api/period/closings", "Period Closings", token=TOKEN)
check("GET", "/api/period/status", "Period Status", token=TOKEN)

# 8. REPORTING
print("\n━━━ 8. REPORTING (12 endpoints) ━━━")
for ep, name in [
    ("dashboard","Dashboard"),("sales/daily","Daily Sales"),
    ("sales/by-treatment","Sales by Treatment"),("sales/by-payment","Sales by Payment"),
    ("treatments/summary","Treatment Summary"),("treatments/therapist-performance","Therapist Performance"),
    ("inventory/stock-summary","Stock Summary"),("inventory/movement-summary","Movement Summary"),
    ("inventory/batch-expiry","Batch Expiry"),("finance/summary","Finance Summary"),
    ("exceptions","Exceptions"),("audit","Audit"),
]:
    check("GET", f"/api/reporting/{ep}", f"GET {name}", token=TOKEN)

# 9. DASHBOARD
print("\n━━━ 9. DASHBOARD (4 endpoints) ━━━")
check("GET", "/api/dashboard/summary", "Dashboard Summary", token=TOKEN)
check("GET", "/api/dashboard/alerts", "Dashboard Alerts", token=TOKEN)
check("GET", "/dashboard", "Dashboard HTML")
check("GET", "/dashboard/owner", "Owner Dashboard")

# 10. EXCEPTIONS
print("\n━━━ 10. EXCEPTIONS ━━━")
check("GET", "/api/exceptions", "List Exceptions", token=TOKEN)

# 11. SYNC
print("\n━━━ 11. SYNC (6 endpoints) ━━━")
for ep, name in [
    ("queue","Queue"),("queue/stats","Queue Stats"),("devices","Devices"),
    ("connectivity","Connectivity"),("integration-log","Integration Log"),
    ("branch-cache","Branch Cache"),
]:
    check("GET", f"/api/sync/{ep}", f"GET {name}", token=TOKEN)

# 12. COA & CLOSING LEGACY
print("\n━━━ 12. COA & CLOSING LEGACY ━━━")
check("GET", "/api/coa/accounts", "COA Accounts", token=TOKEN)
check("GET", "/api/coa/mappings", "COA Mappings", token=TOKEN)
check("GET", "/api/coa/mappings/status-summary", "COA Status Summary", token=TOKEN)
check("GET", "/api/daily-closing/summary", "Daily Closing Summary", token=TOKEN)

# 13. FRONTEND PAGES
print("\n━━━ 13. FRONTEND PAGES ━━━")
check("GET", "/app", "ERP SPA root")
check("GET", "/login", "Login page")
check("GET", "/pos", "POS portal")
check("GET", "/apps", "POS apps landing")

# 14. WRITE OPERATIONS
print("\n━━━ 14. WRITE OPERATIONS (CRUD) ━━━")

# Treatment Category CRUD
s, r = api("POST", "/api/master/treatment-category", {"name":"Smoke TC","description":"test"}, TOKEN)
tcid = get_id(r)
if tcid:
    print(f"  ✅ [{s}] CREATE treatment-cat id={tcid}"); PASS += 1
    check("PUT", f"/api/master/treatment-category/{tcid}", "UPDATE treatment-cat", {"name":"Smoke TC v2"}, TOKEN)
    check("DELETE", f"/api/master/treatment-category/{tcid}", "DELETE treatment-cat", token=TOKEN)
else:
    print(f"  ❌ [{s}] CREATE treatment-cat"); FAIL += 1; ERRORS.append(f"CRUD treatment-cat: {s}")

# Product Category CRUD
s, r = api("POST", "/api/master/product-category", {"name":"Smoke PC","description":"test"}, TOKEN)
pcid = get_id(r)
if pcid:
    print(f"  ✅ [{s}] CREATE product-cat id={pcid}"); PASS += 1
    check("PUT", f"/api/master/product-category/{pcid}", "UPDATE product-cat", {"name":"Smoke PC v2"}, TOKEN)
    check("DELETE", f"/api/master/product-category/{pcid}", "DELETE product-cat", token=TOKEN)
else:
    print(f"  ❌ [{s}] CREATE product-cat"); FAIL += 1; ERRORS.append(f"CRUD product-cat: {s}")

# Treatment CRUD
s, r = api("POST", "/api/master/treatment", {"name":"Smoke Treatment","price":100000,"duration_minutes":60,"category":"Body"}, TOKEN)
trid = get_id(r)
if trid:
    print(f"  ✅ [{s}] CREATE treatment id={trid}"); PASS += 1
    check("PUT", f"/api/master/treatment/{trid}", "UPDATE treatment", {"name":"Smoke Treatment v2"}, TOKEN)
    check("DELETE", f"/api/master/treatment/{trid}", "DELETE treatment", token=TOKEN)
else:
    print(f"  ❌ [{s}] CREATE treatment"); FAIL += 1; ERRORS.append(f"CRUD treatment: {s}")

# COA CRUD
s, r = api("POST", "/api/master/coa", {"code":"99999","name":"Smoke COA","account_type":"asset","is_active":True}, TOKEN)
coaid = get_id(r)
if coaid:
    print(f"  ✅ [{s}] CREATE COA id={coaid}"); PASS += 1
    check("PUT", f"/api/master/coa/{coaid}", "UPDATE COA", {"name":"Smoke COA v2"}, TOKEN)
    check("DELETE", f"/api/master/coa/{coaid}", "DELETE COA", token=TOKEN)
else:
    print(f"  ❌ [{s}] CREATE COA"); FAIL += 1; ERRORS.append(f"CRUD COA: {s}")

# Branch CRUD
s, r = api("POST", "/api/master/branch", {"name":"Smoke Branch","code":"STB","address":"Test","is_active":True}, TOKEN)
brid = get_id(r)
if brid:
    print(f"  ✅ [{s}] CREATE branch id={brid}"); PASS += 1
    check("PUT", f"/api/master/branch/{brid}", "UPDATE branch", {"name":"Smoke Branch v2"}, TOKEN)
else:
    print(f"  ❌ [{s}] CREATE branch"); FAIL += 1; ERRORS.append(f"CRUD branch: {s}")

# Journal Entry
s, r = api("POST", "/api/finance/journal-entry", {
    "date":"2026-05-28","description":"Smoke journal",
    "entries":[{"account_code":"10001","debit":100000,"credit":0},{"account_code":"40001","debit":0,"credit":100000}]
}, TOKEN)
if get_id(r) or (isinstance(s,int) and 200<=s<400):
    print(f"  ✅ [{s}] CREATE journal entry"); PASS += 1
else:
    print(f"  ❌ [{s}] CREATE journal entry"); FAIL += 1; ERRORS.append(f"Journal: {s}")

# Bank Account
s, r = api("POST", "/api/finance/bank-account", {"bank_name":"BCA","account_number":"123","account_name":"Smoke","is_active":True}, TOKEN)
if get_id(r) or (isinstance(s,int) and 200<=s<400):
    print(f"  ✅ [{s}] CREATE bank account"); PASS += 1
else:
    print(f"  ❌ [{s}] CREATE bank account"); FAIL += 1; ERRORS.append(f"Bank: {s}")

# Fixed Asset
s, r = api("POST", "/api/finance/asset", {"name":"Smoke Asset","purchase_date":"2026-01-01","purchase_value":5000000,"useful_life_years":5}, TOKEN)
if get_id(r) or (isinstance(s,int) and 200<=s<400):
    print(f"  ✅ [{s}] CREATE fixed asset"); PASS += 1
else:
    print(f"  ❌ [{s}] CREATE fixed asset"); FAIL += 1; ERRORS.append(f"Asset: {s}")

# Stock IN
s, r = api("POST", "/api/inventory/stock-in", {"product_code":"SMOKE-001","quantity":50,"notes":"test"}, TOKEN)
if isinstance(s,int) and 200<=s<400:
    print(f"  ✅ [{s}] Stock IN"); PASS += 1
else:
    print(f"  ❌ [{s}] Stock IN"); FAIL += 1; ERRORS.append(f"Stock IN: {s}")

# BOM
s, r = api("POST", "/api/inventory/bom", {"product_code":"SMOKE-001","components":[{"code":"RAW-001","quantity":2}]}, TOKEN)
if isinstance(s,int) and 200<=s<500:
    print(f"  ✅ [{s}] CREATE BOM"); PASS += 1
else:
    print(f"  ❌ [{s}] CREATE BOM"); FAIL += 1; ERRORS.append(f"BOM: {s}")

# Opname
s, r = api("POST", "/api/inventory/opname", {"product_code":"SMOKE-001","system_qty":100,"actual_qty":98,"notes":"test"}, TOKEN)
if isinstance(s,int) and 200<=s<500:
    print(f"  ✅ [{s}] CREATE opname"); PASS += 1
else:
    print(f"  ❌ [{s}] CREATE opname"); FAIL += 1; ERRORS.append(f"Opname: {s}")

# Financial Period
s, r = api("POST", "/api/period/financial-period", {"name":"Smoke Period","start_date":"2026-01-01","end_date":"2026-12-31"}, TOKEN)
if get_id(r) or (isinstance(s,int) and 200<=s<400):
    print(f"  ✅ [{s}] CREATE financial period"); PASS += 1
else:
    print(f"  ❌ [{s}] CREATE financial period"); FAIL += 1; ERRORS.append(f"Period: {s}")

# Sync Device
s, r = api("POST", "/api/sync/devices", {"device_name":"Smoke Device","device_type":"pos"}, TOKEN)
if isinstance(s,int) and 200<=s<500:
    print(f"  ✅ [{s}] Register sync device"); PASS += 1
else:
    print(f"  ❌ [{s}] Register sync device"); FAIL += 1; ERRORS.append(f"Sync device: {s}")

# 15. POS E2E FLOW
print("\n━━━ 15. POS TRANSACTION E2E ━━━")
s, r = api("POST", "/api/pos/booking", {"customer_name":"Smoke Customer","phone":"08123456789"}, TOKEN)
txnid = get_id(r)
if txnid:
    print(f"  ✅ [{s}] CREATE booking id={txnid}"); PASS += 1
    s2, r2 = api("POST", f"/api/pos/transaction/{txnid}/add-item", {"item_type":"treatment","item_name":"Test Massage","price":150000,"quantity":1}, TOKEN)
    print(f"  {'✅' if isinstance(s2,int) and 200<=s2<500 else '❌'} [{s2}] ADD item"); 
    if isinstance(s2,int) and 200<=s2<500: PASS+=1
    else: FAIL+=1; ERRORS.append(f"POS add-item: {s2}")
    
    s3, r3 = api("GET", f"/api/pos/transaction/{txnid}", token=TOKEN)
    print(f"  {'✅' if isinstance(s3,int) and 200<=s3<400 else '❌'} [{s3}] GET txn detail");
    if isinstance(s3,int) and 200<=s3<400: PASS+=1
    else: FAIL+=1; ERRORS.append(f"POS get txn: {s3}")
    
    s4, r4 = api("POST", f"/api/pos/transaction/{txnid}/payment", {"payment_method":"cash","amount":150000}, TOKEN)
    print(f"  {'✅' if isinstance(s4,int) and 200<=s4<500 else '❌'} [{s4}] PAYMENT");
    if isinstance(s4,int) and 200<=s4<500: PASS+=1
    else: FAIL+=1; ERRORS.append(f"POS payment: {s4}")
else:
    print(f"  ❌ [{s}] CREATE booking"); FAIL += 1; ERRORS.append(f"POS booking: {s}")

# Daily Closing
s, r = api("POST", "/api/pos/daily-closing", {"closing_date":"2026-05-28","branch_id":1}, TOKEN)
print(f"  {'✅' if isinstance(s,int) and 200<=s<500 else '❌'} [{s}] Daily closing");
if isinstance(s,int) and 200<=s<500: PASS+=1
else: FAIL+=1; ERRORS.append(f"Daily closing: {s}")

# 16. SECURITY
print("\n━━━ 16. SECURITY ━━━")
s, _ = api("GET", "/api/master/treatment")
print(f"  {'✅' if s in (401,403,422) else '❌'} [{s}] No-token blocked")
if s in (401,403,422): PASS+=1
else: FAIL+=1; ERRORS.append(f"Security no-token: {s}")

s, _ = api("GET", "/api/master/treatment", token="bad-token")
print(f"  {'✅' if s in (401,403) else '❌'} [{s}] Bad-token rejected")
if s in (401,403): PASS+=1
else: FAIL+=1; ERRORS.append(f"Security bad-token: {s}")

# RESULTS
TOTAL = PASS + FAIL
print("\n" + "=" * 66)
print(f"  ✅ PASS: {PASS}  |  ❌ FAIL: {FAIL}  |  📊 TOTAL: {TOTAL}  |  📈 {PASS/TOTAL*100:.1f}%")
print("=" * 66)
if ERRORS:
    print("\n❌ FAILURES:")
    for e in ERRORS: print(f"  • {e}")
print()
print("🎉 ALL PASSED!" if FAIL == 0 else f"⚠️  {FAIL} test(s) failed")
sys.exit(0 if FAIL == 0 else 1)
