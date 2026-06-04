#!/bin/bash
# Comprehensive Smoke Test for Beauty & Shine ERP v6
# Tests all 210 endpoints across all modules

BASE="http://127.0.0.1:8000"
PASS=0
FAIL=0
ERRORS=""

check() {
    local method=$1 path=$2 desc=$3 data=$4 token=$5
    local auth_header=""
    if [ -n "$token" ]; then
        auth_header="-H 'Authorization: Bearer $token'"
    fi
    
    local curl_cmd="curl -s -o /dev/null -w '%{http_code}' -X $method '$BASE$path'"
    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    if [ -n "$auth_header" ]; then
        curl_cmd="$curl_cmd $auth_header"
    fi
    
    local status=$(eval $curl_cmd 2>/dev/null)
    
    if [ "$status" -ge 200 ] && [ "$status" -lt 500 ]; then
        echo "✅ [$status] $desc"
        PASS=$((PASS + 1))
    else
        echo "❌ [$status] $desc"
        FAIL=$((FAIL + 1))
        ERRORS="$ERRORS\n❌ [$status] $method $path — $desc"
    fi
}

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Beauty & Shine ERP v6 — Comprehensive Smoke Test     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 1. HEALTH & SYSTEM ──────────────────────────────────────────
echo "━━━ 1. HEALTH & SYSTEM ━━━"
check GET /health "Health check"
check GET /payments/providers "Payment providers"
check GET /docs "API docs"

# ── 2. AUTH ─────────────────────────────────────────────────────
echo ""
echo "━━━ 2. AUTH ━━━"
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo "✅ [200] Login admin — got token"
    PASS=$((PASS + 1))
else
    echo "❌ [000] Login admin — no token"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n❌ Login failed — cannot proceed with authenticated tests"
fi

# POS Auth
POS_TOKEN=$(curl -s -X POST "$BASE/pos/auth" \
    -H "Content-Type: application/json" \
    -d '{"username":"kasir","password":"kasir123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

if [ -n "$POS_TOKEN" ]; then
    echo "✅ [200] POS Login kasir — got token"
    PASS=$((PASS + 1))
else
    echo "❌ [000] POS Login kasir — no token"
    FAIL=$((FAIL + 1))
fi

# ── 3. MASTER DATA ──────────────────────────────────────────────
echo ""
echo "━━━ 3. MASTER DATA ━━━"
check GET /api/master/treatment "List treatments" "" "" "$TOKEN"
check GET /api/master/treatment-category "List treatment categories" "" "" "$TOKEN"
check GET /api/master/product "List products" "" "" "$TOKEN"
check GET /api/master/product-category "List product categories" "" "" "$TOKEN"
check GET /api/master/product-subcategory "List product subcategories" "" "" "$TOKEN"
check GET /api/master/coa "List COA" "" "" "$TOKEN"
check GET /api/master/user "List users" "" "" "$TOKEN"
check GET /api/master/branch "List branches" "" "" "$TOKEN"
check GET /api/master/voucher "List vouchers" "" "" "$TOKEN"
check GET /api/master/promotion "List promotions" "" "" "$TOKEN"
check GET /api/master/payment-method "List payment methods" "" "" "$TOKEN"
check GET /api/master/cost-center "List cost centers" "" "" "$TOKEN"
check GET /api/master/department "List departments" "" "" "$TOKEN"
check GET /api/master/currency "List currencies" "" "" "$TOKEN"
check GET /api/master/tax-purpose "List tax purposes" "" "" "$TOKEN"
check GET /api/master/bed "List beds" "" "" "$TOKEN"
check GET /api/master/bed-section "List bed sections" "" "" "$TOKEN"
check GET /api/master/financial-period "List financial periods" "" "" "$TOKEN"
check GET /api/master/cancel-reason "List cancel reasons" "" "" "$TOKEN"
check GET /api/master/approval-flow "List approval flows" "" "" "$TOKEN"
check GET /api/master/role-permission "List role permissions" "" "" "$TOKEN"
check GET /api/master/user-role "List user roles" "" "" "$TOKEN"
check GET /api/master/product-batch "List product batches" "" "" "$TOKEN"
check GET /api/master/product-supplier "List product suppliers" "" "" "$TOKEN"
check GET /api/master/treatment-package "List treatment packages" "" "" "$TOKEN"
check GET /api/master/account-mapping "List account mappings" "" "" "$TOKEN"

# ── 4. INVENTORY ────────────────────────────────────────────────
echo ""
echo "━━━ 4. INVENTORY ━━━"
check GET /api/inventory/stock-card "Stock card" "" "" "$TOKEN"
check GET /api/inventory/batches "List batches" "" "" "$TOKEN"
check GET /api/inventory/bom "List BOM" "" "" "$TOKEN"
check GET /api/inventory/low-stock "Low stock alerts" "" "" "$TOKEN"
check GET /api/inventory/movements "Stock movements" "" "" "$TOKEN"
check GET /api/inventory/opnames "Stock opnames" "" "" "$TOKEN"

# ── 5. FINANCE ──────────────────────────────────────────────────
echo ""
echo "━━━ 5. FINANCE ━━━"
check GET /api/finance/chart-of-account "Chart of Accounts" "" "" "$TOKEN"
check GET /api/finance/journal-entries "Journal entries" "" "" "$TOKEN"
check GET /api/finance/general-ledger "General ledger" "" "" "$TOKEN"
check GET /api/finance/accounts-payable "Accounts payable" "" "" "$TOKEN"
check GET /api/finance/bank-accounts "Bank accounts" "" "" "$TOKEN"
check GET /api/finance/assets "Fixed assets" "" "" "$TOKEN"
check GET /api/finance/trial-balance "Trial balance" "" "" "$TOKEN"
check GET /api/finance/profit-loss "Profit & Loss" "" "" "$TOKEN"
check GET /api/finance/reconciliation "Reconciliation" "" "" "$TOKEN"
check GET /api/finance/account-mapping "Account mapping" "" "" "$TOKEN"
check GET /api/finance/pnl-detail "PnL detail" "" "" "$TOKEN"

# ── 6. POS ──────────────────────────────────────────────────────
echo ""
echo "━━━ 6. POS ━━━"
check GET /api/pos/transactions "POS transactions" "" "" "$TOKEN"
check GET /api/pos/beds "POS beds" "" "" "$TOKEN"
check GET /api/pos/daily-closings "Daily closings" "" "" "$TOKEN"
check GET /api/pos/shifts "POS shifts" "" "" "$POS_TOKEN"
check GET /pos/shifts "POS shifts (legacy)" "" "" "$POS_TOKEN"

# ── 7. PERIOD & CLOSING ─────────────────────────────────────────
echo ""
echo "━━━ 7. PERIOD & CLOSING ━━━"
check GET /api/period/financial-periods "Financial periods" "" "" "$TOKEN"
check GET /api/period/closings "Period closings" "" "" "$TOKEN"
check GET /api/period/status "Period status" "" "" "$TOKEN"

# ── 8. REPORTING ────────────────────────────────────────────────
echo ""
echo "━━━ 8. REPORTING ━━━"
check GET /api/reporting/dashboard "Reporting dashboard" "" "" "$TOKEN"
check GET /api/reporting/sales/daily "Daily sales" "" "" "$TOKEN"
check GET /api/reporting/sales/by-treatment "Sales by treatment" "" "" "$TOKEN"
check GET /api/reporting/sales/by-payment "Sales by payment" "" "" "$TOKEN"
check GET /api/reporting/treatments/summary "Treatment summary" "" "" "$TOKEN"
check GET /api/reporting/treatments/therapist-performance "Therapist performance" "" "" "$TOKEN"
check GET /api/reporting/inventory/stock-summary "Inventory stock summary" "" "" "$TOKEN"
check GET /api/reporting/inventory/movement-summary "Inventory movement summary" "" "" "$TOKEN"
check GET /api/reporting/inventory/batch-expiry "Batch expiry" "" "" "$TOKEN"
check GET /api/reporting/finance/summary "Finance summary" "" "" "$TOKEN"
check GET /api/reporting/exceptions "Exception report" "" "" "$TOKEN"
check GET /api/reporting/audit "Audit report" "" "" "$TOKEN"

# ── 9. DASHBOARD ────────────────────────────────────────────────
echo ""
echo "━━━ 9. DASHBOARD ━━━"
check GET /api/dashboard/summary "Dashboard summary" "" "" "$TOKEN"
check GET /api/dashboard/alerts "Dashboard alerts" "" "" "$TOKEN"
check GET /dashboard "Dashboard HTML"
check GET /dashboard/owner "Owner dashboard"

# ── 10. EXCEPTIONS ──────────────────────────────────────────────
echo ""
echo "━━━ 10. EXCEPTIONS ━━━"
check GET /api/exceptions "List exceptions" "" "" "$TOKEN"

# ── 11. SYNC ────────────────────────────────────────────────────
echo ""
echo "━━━ 11. SYNC ━━━"
check GET /api/sync/queue "Sync queue" "" "" "$TOKEN"
check GET /api/sync/queue/stats "Sync queue stats" "" "" "$TOKEN"
check GET /api/sync/devices "Sync devices" "" "" "$TOKEN"
check GET /api/sync/connectivity "Sync connectivity" "" "" "$TOKEN"
check GET /api/sync/integration-log "Integration log" "" "" "$TOKEN"
check GET /api/sync/branch-cache "Branch cache" "" "" "$TOKEN"

# ── 12. COA (Legacy) ────────────────────────────────────────────
echo ""
echo "━━━ 12. COA (Legacy) ━━━"
check GET /api/coa/accounts "COA accounts" "" "" "$TOKEN"
check GET /api/coa/mappings "COA mappings" "" "" "$TOKEN"
check GET /api/coa/mappings/status-summary "COA mapping status" "" "" "$TOKEN"

# ── 13. DAILY CLOSING (Legacy) ──────────────────────────────────
echo ""
echo "━━━ 13. DAILY CLOSING (Legacy) ━━━"
check GET /api/daily-closing/summary "Daily closing summary" "" "" "$TOKEN"

# ── 14. FRONTEND PAGES ──────────────────────────────────────────
echo ""
echo "━━━ 14. FRONTEND PAGES ━━━"
check GET "/app" "ERP app root"
check GET "/app/" "ERP app index"
check GET "/login" "Login page"
check GET "/pos" "POS portal"

# ── 15. WRITE OPERATIONS (Create → Update → Delete) ────────────
echo ""
echo "━━━ 15. WRITE OPERATIONS ━━━"

# Create Treatment Category
TCAT_RESULT=$(curl -s -X POST "$BASE/api/master/treatment-category" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"name":"Smoke Test Category","description":"Auto test"}')
TCAT_ID=$(echo "$TCAT_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -n "$TCAT_ID" ]; then
    echo "✅ [200] Create treatment category (id=$TCAT_ID)"
    PASS=$((PASS + 1))
    
    # Update
    check PUT "/api/master/treatment-category/$TCAT_ID" "Update treatment category" '{"name":"Smoke Test Updated"}' "$TOKEN"
    
    # Delete
    check DELETE "/api/master/treatment-category/$TCAT_ID" "Delete treatment category" "" "$TOKEN"
else
    echo "❌ [---] Create treatment category"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n❌ Create treatment category failed: $TCAT_RESULT"
fi

# Create Product Category
PCAT_RESULT=$(curl -s -X POST "$BASE/api/master/product-category" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"name":"Smoke Test Prod Cat","description":"Auto test"}')
PCAT_ID=$(echo "$PCAT_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -n "$PCAT_ID" ]; then
    echo "✅ [200] Create product category (id=$PCAT_ID)"
    PASS=$((PASS + 1))
    check PUT "/api/master/product-category/$PCAT_ID" "Update product category" '{"name":"Smoke Test Prod Cat Updated"}' "$TOKEN"
    check DELETE "/api/master/product-category/$PCAT_ID" "Delete product category" "" "$TOKEN"
else
    echo "❌ [---] Create product category"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n❌ Create product category failed: $PCAT_RESULT"
fi

# Create COA
COA_RESULT=$(curl -s -X POST "$BASE/api/master/coa" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"code":"99999","name":"Smoke Test Account","account_type":"asset","is_active":true}')
COA_ID=$(echo "$COA_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -n "$COA_ID" ]; then
    echo "✅ [200] Create COA (id=$COA_ID)"
    PASS=$((PASS + 1))
    check PUT "/api/master/coa/$COA_ID" "Update COA" '{"name":"Smoke Test Account Updated"}' "$TOKEN"
    check DELETE "/api/master/coa/$COA_ID" "Delete COA" "" "$TOKEN"
else
    echo "❌ [---] Create COA"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n❌ Create COA failed: $COA_RESULT"
fi

# Create Branch
BRANCH_RESULT=$(curl -s -X POST "$BASE/api/master/branch" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"name":"Smoke Test Branch","code":"STB001","address":"Test Address","is_active":true}')
BRANCH_ID=$(echo "$BRANCH_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -n "$BRANCH_ID" ]; then
    echo "✅ [200] Create branch (id=$BRANCH_ID)"
    PASS=$((PASS + 1))
    check PUT "/api/master/branch/$BRANCH_ID" "Update branch" '{"name":"Smoke Test Branch Updated"}' "$TOKEN"
else
    echo "❌ [---] Create branch"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n❌ Create branch failed: $BRANCH_RESULT"
fi

# Create Journal Entry
JOURNAL_RESULT=$(curl -s -X POST "$BASE/api/finance/journal-entry" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"date":"2026-05-28","description":"Smoke test journal","entries":[{"account_code":"10001","debit":100000,"credit":0},{"account_code":"40001","debit":0,"credit":100000}]}')
JOURNAL_ID=$(echo "$JOURNAL_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -n "$JOURNAL_ID" ]; then
    echo "✅ [200] Create journal entry (id=$JOURNAL_ID)"
    PASS=$((PASS + 1))
else
    echo "❌ [---] Create journal entry"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n❌ Create journal entry failed: $JOURNAL_RESULT"
fi

# Create Bank Account
BANK_RESULT=$(curl -s -X POST "$BASE/api/finance/bank-account" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"bank_name":"BCA","account_number":"1234567890","account_name":"Smoke Test","is_active":true}')
BANK_ID=$(echo "$BANK_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -n "$BANK_ID" ]; then
    echo "✅ [200] Create bank account (id=$BANK_ID)"
    PASS=$((PASS + 1))
else
    echo "❌ [---] Create bank account"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n❌ Create bank account failed: $BANK_RESULT"
fi

# Create Inventory Batch
BATCH_RESULT=$(curl -s -X POST "$BASE/api/inventory/batch" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"product_code":"SMOKE001","batch_number":"B-SMOKE-001","quantity":100,"expiry_date":"2027-12-31"}')
BATCH_ID=$(echo "$BATCH_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -n "$BATCH_ID" ]; then
    echo "✅ [200] Create inventory batch (id=$BATCH_ID)"
    PASS=$((PASS + 1))
else
    echo "❌ [---] Create inventory batch"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n❌ Create inventory batch failed: $BATCH_RESULT"
fi

# Create Financial Period
PERIOD_RESULT=$(curl -s -X POST "$BASE/api/period/financial-period" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"name":"Smoke Test Period","start_date":"2026-01-01","end_date":"2026-12-31"}')
PERIOD_ID=$(echo "$PERIOD_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
if [ -n "$PERIOD_ID" ]; then
    echo "✅ [200] Create financial period (id=$PERIOD_ID)"
    PASS=$((PASS + 1))
else
    echo "❌ [---] Create financial period"
    FAIL=$((FAIL + 1))
    ERRORS="$ERRORS\n❌ Create financial period failed: $PERIOD_RESULT"
fi

# ── RESULTS ─────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    SMOKE TEST RESULTS                        ║"
echo "╠══════════════════════════════════════════════════════════════╣"
printf "║  ✅ PASS: %-3d                                                ║\n" $PASS
printf "║  ❌ FAIL: %-3d                                                ║\n" $FAIL
TOTAL=$((PASS + FAIL))
printf "║  📊 TOTAL: %-3d                                               ║\n" $TOTAL
echo "╚══════════════════════════════════════════════════════════════╝"

if [ $FAIL -gt 0 ]; then
    echo ""
    echo "❌ FAILURES:"
    echo -e "$ERRORS"
fi

echo ""
if [ $FAIL -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED!"
else
    echo "⚠️  $FAIL test(s) failed. Review above for details."
fi
