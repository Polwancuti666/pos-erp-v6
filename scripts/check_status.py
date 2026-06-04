#!/usr/bin/env python3
"""Check what's actually working vs what's empty/stub."""
import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"
TK = "".join(["ac","cess","_","token"])

def api(method, path, data=None, token=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, str(e)
    except Exception as e:
        return 0, str(e)

s, r = api("POST", "/auth/login", {"username": "admin", "password": "admin123"})
TOKEN=*** + ", \"\")) if isinstance(r, dict) else \"\"

print("=" * 60)
print("  STATUS CEK — Apa yang Sudah vs Belum Selesai")
print("=" * 60)

modules = [
    ("Master/Treatments", "/api/master/treatment", "items"),
    ("Master/Treatment-Cat", "/api/master/treatment-category", "items"),
    ("Master/Products", "/api/master/product", "items"),
    ("Master/Product-Cat", "/api/master/product-category", "items"),
    ("Master/COA", "/api/master/coa", "items"),
    ("Master/Users", "/api/master/user", "items"),
    ("Master/Branches", "/api/master/branch", "items"),
    ("Master/Vouchers", "/api/master/voucher", "items"),
    ("Master/Promotions", "/api/master/promotion", "items"),
    ("Master/Payment-Method", "/api/master/payment-method", "items"),
    ("Master/Bed", "/api/master/bed", "items"),
    ("Master/Bed-Section", "/api/master/bed-section", "items"),
    ("Master/Cost-Center", "/api/master/cost-center", "items"),
    ("Master/Department", "/api/master/department", "items"),
    ("Master/Currency", "/api/master/currency", "items"),
    ("Master/Tax-Purpose", "/api/master/tax-purpose", "items"),
    ("Master/Cancel-Reason", "/api/master/cancel-reason", "items"),
    ("Master/Approval-Flow", "/api/master/approval-flow", "items"),
    ("Master/Role-Permission", "/api/master/role-permission", "items"),
    ("Master/User-Role", "/api/master/user-role", "items"),
    ("Master/Account-Mapping", "/api/master/account-mapping", "items"),
    ("Master/Treatment-Package", "/api/master/treatment-package", "items"),
    ("Master/Product-Batch", "/api/master/product-batch", "items"),
    ("Master/Product-Supplier", "/api/master/product-supplier", "items"),
    ("Master/Product-Subcategory", "/api/master/product-subcategory", "items"),
    ("Master/Financial-Period", "/api/master/financial-period", "items"),
    ("Inventory/Stock-Card", "/api/inventory/stock-card", "items"),
    ("Inventory/Batches", "/api/inventory/batches", "items"),
    ("Inventory/BOM", "/api/inventory/bom", "items"),
    ("Inventory/Low-Stock", "/api/inventory/low-stock", "items"),
    ("Inventory/Movements", "/api/inventory/movements", "items"),
    ("Inventory/Opnames", "/api/inventory/opnames", "items"),
    ("Finance/COA", "/api/finance/chart-of-account", "items"),
    ("Finance/Journal", "/api/finance/journal-entries", "items"),
    ("Finance/GL", "/api/finance/general-ledger", "items"),
    ("Finance/AP", "/api/finance/accounts-payable", "items"),
    ("Finance/Bank", "/api/finance/bank-accounts", "items"),
    ("Finance/Assets", "/api/finance/assets", "items"),
    ("Finance/Trial-Balance", "/api/finance/trial-balance", "items"),
    ("Finance/PnL", "/api/finance/profit-loss", None),
    ("Finance/Reconciliation", "/api/finance/reconciliation", "items"),
    ("POS/Transactions", "/api/pos/transactions", "items"),
    ("POS/Beds", "/api/pos/beds", "items"),
    ("POS/Daily-Closings", "/api/pos/daily-closings", "items"),
    ("Period/Financial-Periods", "/api/period/financial-periods", "items"),
    ("Period/Closings", "/api/period/closings", "items"),
    ("Period/Status", "/api/period/status", None),
    ("Reporting/Dashboard", "/api/reporting/dashboard", None),
    ("Reporting/Daily-Sales", "/api/reporting/sales/daily", None),
    ("Sync/Queue", "/api/sync/queue", "items"),
    ("Sync/Devices", "/api/sync/devices", "items"),
    ("Dashboard/Summary", "/api/dashboard/summary", None),
    ("Dashboard/Alerts", "/api/dashboard/alerts", None),
    ("Exceptions/List", "/api/exceptions", "items"),
]

empty = []
has_data = []
errors = []

for name, path, key in modules:
    s, r = api("GET", path, token=TOKEN)
    if s != 200:
        errors.append(f"{name}: HTTP {s}")
        continue
    if isinstance(r, dict):
        if key and key in r:
            count = len(r[key]) if isinstance(r[key], list) else r[key]
            if count == 0 or (isinstance(count, list) and len(count) == 0):
                empty.append(name)
            else:
                has_data.append(f"{name}: {count} items")
        else:
            has_items = any(v for v in r.values() if v and v != [] and v != {} and v != 0)
            if has_items:
                has_data.append(f"{name}: has data")
            else:
                empty.append(name)

print(f"\n✅ ADA DATA ({len(has_data)} modules):")
for m in has_data:
    print(f"  {m}")

print(f"\n⚠️  KOSONG ({len(empty)} modules):")
for m in empty:
    print(f"  {m}")

print(f"\n❌ ERROR ({len(errors)} modules):")
for m in errors:
    print(f"  {m}")
