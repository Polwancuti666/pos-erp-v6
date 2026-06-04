# 08 — Verification & UAT

Complete guide for verifying the migration and running User Acceptance Tests.

## Overview

This guide covers:

1. System verification tests
2. API endpoint tests
3. Frontend tests
4. Database integrity tests
5. Performance tests
6. User Acceptance Testing (UAT)

---

## Step 1: System Verification

### Run System Verification Script

```bash
# Create comprehensive verification script
cat > /var/www/pos-erp-v6/scripts/verify-system.sh << 'SCRIPT'
#!/bin/bash
# System verification script

echo "=== POS ERP System Verification ==="
echo "Date: $(date)"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

# Helper function
check() {
    if [ $1 -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} $2"
        ((PASS++))
    else
        echo -e "  ${RED}✗${NC} $2"
        ((FAIL++))
    fi
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    ((WARN++))
}

# 1. System Services
echo "1. System Services"
systemctl is-active pos-erp > /dev/null 2>&1
check $? "pos-erp service is active"

systemctl is-active nginx > /dev/null 2>&1
check $? "nginx service is active"

systemctl is-active fail2ban > /dev/null 2>&1
check $? "fail2ban service is active"

echo ""

# 2. Network
echo "2. Network"
curl -s http://localhost:8000/health > /dev/null 2>&1
check $? "API health endpoint accessible"

curl -s http://localhost:80 > /dev/null 2>&1
check $? "HTTP port accessible"

curl -s https://localhost:443 > /dev/null 2>&1
check $? "HTTPS port accessible"

echo ""

# 3. SSL Certificate
echo "3. SSL Certificate"
SSL_EXPIRY=$(echo | openssl s_client -servername beautynshine.web.id -connect beautynshine.web.id:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$SSL_EXPIRY" ]; then
    DAYS_LEFT=$(( ($(date -d "$SSL_EXPIRY" +%s) - $(date +%s)) / 86400 ))
    if [ $DAYS_LEFT -gt 30 ]; then
        check 0 "SSL certificate valid ($DAYS_LEFT days remaining)"
    else
        warn "SSL certificate expires in $DAYS_LEFT days"
    fi
else
    check 1 "SSL certificate check"
fi

echo ""

# 4. Database
echo "4. Database"
if [ -f /var/www/pos-erp-v6/pos_erp.db ]; then
    check 0 "Database file exists"
    
    INTEGRITY=$(sqlite3 /var/www/pos-erp-v6/pos_erp.db "PRAGMA integrity_check;")
    if [ "$INTEGRITY" = "ok" ]; then
        check 0 "Database integrity check"
    else
        check 1 "Database integrity check"
    fi
    
    DB_SIZE=$(ls -lh /var/www/pos-erp-v6/pos_erp.db | awk '{print $5}')
    echo "  📊 Database size: $DB_SIZE"
else
    check 1 "Database file exists"
fi

echo ""

# 5. File Permissions
echo "5. File Permissions"
if [ -r /var/www/pos-erp-v6/.env ]; then
    check 0 ".env file readable"
else
    check 1 ".env file readable"
fi

if [ -d /var/www/pos-erp-v6/logs ]; then
    check 0 "Logs directory exists"
else
    check 1 "Logs directory exists"
fi

if [ -d /var/www/pos-erp-v6/static ]; then
    check 0 "Static directory exists"
else
    check 1 "Static directory exists"
fi

echo ""

# 6. Disk Space
echo "6. Disk Space"
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    check 0 "Disk usage: $DISK_USAGE%"
elif [ $DISK_USAGE -lt 90 ]; then
    warn "Disk usage: $DISK_USAGE%"
else
    check 1 "Disk usage: $DISK_USAGE%"
fi

echo ""

# 7. Memory
echo "7. Memory"
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEM_USAGE -lt 80 ]; then
    check 0 "Memory usage: $MEM_USAGE%"
elif [ $MEM_USAGE -lt 90 ]; then
    warn "Memory usage: $MEM_USAGE%"
else
    check 1 "Memory usage: $MEM_USAGE%"
fi

echo ""

# 8. Backups
echo "8. Backups"
BACKUP_COUNT=$(ls /var/www/pos-erp-v6/backups/*.gz 2>/dev/null | wc -l)
if [ $BACKUP_COUNT -gt 0 ]; then
    check 0 "Backups available: $BACKUP_COUNT files"
else
    warn "No backups found"
fi

echo ""

# Summary
echo "=== Verification Summary ==="
echo -e "  ${GREEN}Passed: $PASS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"
echo -e "  ${YELLOW}Warnings: $WARN${NC}"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ System verification PASSED${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ System verification FAILED${NC}"
    exit 1
fi
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/verify-system.sh
```

### Run Verification

```bash
# Run verification script
/var/www/pos-erp-v6/scripts/verify-system.sh
```

---

## Step 2: API Endpoint Tests

### Test All API Endpoints

```bash
# Create API test script
cat > /var/www/pos-erp-v6/scripts/test-api.sh << 'SCRIPT'
#!/bin/bash
# API endpoint test script

BASE_URL="http://localhost:8000"
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_status=$3
    local description=$4
    
    if [ "$method" = "GET" ]; then
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")
    else
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$BASE_URL$endpoint")
    fi
    
    if [ "$STATUS" = "$expected_status" ]; then
        echo -e "  ${GREEN}✓${NC} $description (HTTP $STATUS)"
        ((PASS++))
    else
        echo -e "  ${RED}✗${NC} $description (Expected: $expected_status, Got: $STATUS)"
        ((FAIL++))
    fi
}

echo "=== API Endpoint Tests ==="
echo ""

# Health endpoint
echo "1. Health Endpoints"
test_endpoint GET "/health" "200" "Health check"

# Documentation
echo ""
echo "2. Documentation"
test_endpoint GET "/docs" "200" "Swagger UI"
test_endpoint GET "/redoc" "200" "ReDoc"

# API v1 endpoints
echo ""
echo "3. API v1 Endpoints"
test_endpoint GET "/api/v1/branches" "200" "List branches"
test_endpoint GET "/api/v1/products" "200" "List products"
test_endpoint GET "/api/v1/categories" "200" "List categories"
test_endpoint GET "/api/v1/users" "200" "List users"

# POS endpoints
echo ""
echo "4. POS Endpoints"
test_endpoint GET "/api/v1/pos/shifts" "200" "List shifts"
test_endpoint GET "/api/v1/pos/transactions" "200" "List transactions"

# Finance endpoints
echo ""
echo "5. Finance Endpoints"
test_endpoint GET "/api/v1/finance/accounts" "200" "List accounts"
test_endpoint GET "/api/v1/finance/journals" "200" "List journals"

# Inventory endpoints
echo ""
echo "6. Inventory Endpoints"
test_endpoint GET "/api/v1/inventory/movements" "200" "List inventory movements"
test_endpoint GET "/api/v1/inventory/stock" "200" "List stock"

echo ""
echo "=== Test Summary ==="
echo -e "  ${GREEN}Passed: $PASS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All API tests PASSED${NC}"
else
    echo ""
    echo -e "${RED}✗ Some API tests FAILED${NC}"
fi
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/test-api.sh
```

### Run API Tests

```bash
# Run API tests
/var/www/pos-erp-v6/scripts/test-api.sh
```

---

## Step 3: Frontend Tests

### Test Frontend Accessibility

```bash
# Create frontend test script
cat > /var/www/pos-erp-v6/scripts/test-frontend.sh << 'SCRIPT'
#!/bin/bash
# Frontend test script

BASE_URL="https://beautynshine.web.id"
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

test_page() {
    local url=$1
    local description=$2
    
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$STATUS" = "200" ]; then
        echo -e "  ${GREEN}✓${NC} $description (HTTP $STATUS)"
        ((PASS++))
    else
        echo -e "  ${RED}✗${NC} $description (HTTP $STATUS)"
        ((FAIL++))
    fi
}

echo "=== Frontend Tests ==="
echo ""

# Main pages
echo "1. Main Pages"
test_page "$BASE_URL" "Home page"
test_page "$BASE_URL/login" "Login page"
test_page "$BASE_URL/dashboard" "Dashboard"
test_page "$BASE_URL/pos" "POS page"
test_page "$BASE_URL/master" "Master data"
test_page "$BASE_URL/inventory" "Inventory"
test_page "$BASE_URL/finance" "Finance"
test_page "$BASE_URL/reporting" "Reporting"

# Static assets
echo ""
echo "2. Static Assets"
test_page "$BASE_URL/favicon.ico" "Favicon"

echo ""
echo "=== Test Summary ==="
echo -e "  ${GREEN}Passed: $PASS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All frontend tests PASSED${NC}"
else
    echo ""
    echo -e "${RED}✗ Some frontend tests FAILED${NC}"
fi
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/test-frontend.sh
```

### Run Frontend Tests

```bash
# Run frontend tests
/var/www/pos-erp-v6/scripts/test-frontend.sh
```

---

## Step 4: Database Integrity Tests

### Verify Database Data

```bash
# Create database test script
cat > /var/www/pos-erp-v6/scripts/test-database.sh << 'SCRIPT'
#!/bin/bash
# Database integrity test script

DB_PATH="/var/www/pos-erp-v6/pos_erp.db"
PASS=0
FAIL=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check_query() {
    local query=$1
    local description=$2
    local expected=$3
    
    RESULT=$(sqlite3 "$DB_PATH" "$query" 2>/dev/null)
    
    if [ "$RESULT" = "$expected" ]; then
        echo -e "  ${GREEN}✓${NC} $description"
        ((PASS++))
    else
        echo -e "  ${RED}✗${NC} $description (Expected: $expected, Got: $RESULT)"
        ((FAIL++))
    fi
}

check_exists() {
    local table=$1
    local description=$2
    
    EXISTS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='$table';")
    
    if [ "$EXISTS" = "1" ]; then
        echo -e "  ${GREEN}✓${NC} $description"
        ((PASS++))
    else
        echo -e "  ${RED}✗${NC} $description"
        ((FAIL++))
    fi
}

echo "=== Database Integrity Tests ==="
echo ""

# Table existence
echo "1. Table Existence"
check_exists "branch" "Branch table exists"
check_exists "users" "Users table exists"
check_exists "product" "Product table exists"
check_exists "txn" "Transaction table exists"
check_exists "inventory_move" "Inventory move table exists"
check_exists "journal" "Journal table exists"
check_exists "account" "Account table exists"

echo ""

# Data integrity
echo "2. Data Integrity"
check_query "PRAGMA integrity_check;" "Database integrity" "ok"
check_query "PRAGMA foreign_key_check;" "Foreign key integrity" ""

echo ""

# Record counts
echo "3. Record Counts"
BRANCH_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM branch;")
echo "  📊 Branches: $BRANCH_COUNT"

USER_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM users;")
echo "  📊 Users: $USER_COUNT"

PRODUCT_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM product;")
echo "  📊 Products: $PRODUCT_COUNT"

TXN_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM txn;")
echo "  📊 Transactions: $TXN_COUNT"

echo ""

# Index verification
echo "4. Index Verification"
INDEX_COUNT=$(sqlite3 "$DB_PATH" ".indexes" | wc -l)
echo "  📊 Indexes: $INDEX_COUNT"

echo ""
echo "=== Test Summary ==="
echo -e "  ${GREEN}Passed: $PASS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ All database tests PASSED${NC}"
else
    echo ""
    echo -e "${RED}✗ Some database tests FAILED${NC}"
fi
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/test-database.sh
```

### Run Database Tests

```bash
# Run database tests
/var/www/pos-erp-v6/scripts/test-database.sh
```

---

## Step 5: Performance Tests

### Load Testing (Optional)

```bash
# Install Apache Bench
apt install -y apache2-utils

# Test API performance
ab -n 1000 -c 10 http://localhost:8000/health

# Expected results:
# - Requests per second: > 100
# - Time per request: < 100ms
# - Failed requests: 0
```

### Database Performance

```bash
# Test query performance
time sqlite3 /var/www/pos-erp-v6/pos_erp.db "SELECT COUNT(*) FROM txn;"
time sqlite3 /var/www/pos-erp-v6/pos_erp.db "SELECT * FROM product LIMIT 100;"
```

---

## Step 6: User Acceptance Testing (UAT)

### UAT Checklist

#### Authentication
- [ ] Login with valid credentials
- [ ] Login with invalid credentials (should fail)
- [ ] Logout functionality
- [ ] Password reset (if implemented)

#### POS Module
- [ ] Open shift
- [ ] Create new transaction
- [ ] Add items to transaction
- [ ] Apply discount
- [ ] Process payment (cash)
- [ ] Process payment (non-cash)
- [ ] Print receipt
- [ ] Close shift
- [ ] Daily closing

#### Inventory Module
- [ ] View product list
- [ ] Add new product
- [ ] Edit product
- [ ] View stock levels
- [ ] Record stock in
- [ ] Record stock out
- [ ] Stock adjustment
- [ ] Inventory report

#### Finance Module
- [ ] View chart of accounts
- [ ] Create journal entry
- [ ] Post journal entry
- [ ] View trial balance
- [ ] View profit & loss
- [ ] View balance sheet
- [ ] Bank reconciliation

#### Master Data
- [ ] Manage branches
- [ ] Manage users
- [ ] Manage categories
- [ ] Manage suppliers
- [ ] Manage customers

#### Reporting
- [ ] Sales report
- [ ] Inventory report
- [ ] Financial report
- [ ] Export to Excel
- [ ] Export to PDF

---

## Step 7: Run All Tests

### Create Master Test Script

```bash
# Create master test script
cat > /var/www/pos-erp-v6/scripts/run-all-tests.sh << 'SCRIPT'
#!/bin/bash
# Master test script

echo "=== POS ERP Complete Test Suite ==="
echo "Date: $(date)"
echo ""

TOTAL_PASS=0
TOTAL_FAIL=0

# Run system verification
echo "Running system verification..."
/var/www/pos-erp-v6/scripts/verify-system.sh
SYSTEM_EXIT=$?

echo ""

# Run API tests
echo "Running API tests..."
/var/www/pos-erp-v6/scripts/test-api.sh
API_EXIT=$?

echo ""

# Run frontend tests
echo "Running frontend tests..."
/var/www/pos-erp-v6/scripts/test-frontend.sh
FRONTEND_EXIT=$?

echo ""

# Run database tests
echo "Running database tests..."
/var/www/pos-erp-v6/scripts/test-database.sh
DB_EXIT=$?

echo ""

# Summary
echo "=== Test Suite Summary ==="
if [ $SYSTEM_EXIT -eq 0 ] && [ $API_EXIT -eq 0 ] && [ $FRONTEND_EXIT -eq 0 ] && [ $DB_EXIT -eq 0 ]; then
    echo "✓ All test suites PASSED"
    exit 0
else
    echo "✗ Some test suites FAILED"
    exit 1
fi
SCRIPT

chmod +x /var/www/pos-erp-v6/scripts/run-all-tests.sh
```

### Run All Tests

```bash
# Run complete test suite
/var/www/pos-erp-v6/scripts/run-all-tests.sh
```

---

## Post-Verification Checklist

After all tests pass:

- [ ] System verification passed
- [ ] API tests passed
- [ ] Frontend tests passed
- [ ] Database tests passed
- [ ] Performance acceptable
- [ ] UAT checklist completed
- [ ] Documentation updated
- [ ] Team notified of migration completion

---

## Next Steps

After verification is complete:

1. Update documentation with new server details
2. Notify team of migration completion
3. Monitor system for 24-48 hours
4. Schedule old server decommission (after 7 days)

---

**Estimated Time:** 1-2 hours (including UAT)
