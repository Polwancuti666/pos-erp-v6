#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — Backup Verification Script
# =============================================================================
# Verifies that a backup is complete and ready for restore.
#
# Usage:
#   ./verify-backup.sh --backup BACKUP_PATH
#
# Options:
#   --backup PATH    Path to backup file (.tar.gz) or directory
#   --verbose        Show detailed output
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================
BACKUP_PATH=""
VERBOSE=false

# =============================================================================
# Colors
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --backup)
            BACKUP_PATH="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Helper Functions
# =============================================================================
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

info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "  ${BLUE}ℹ${NC} $1"
    fi
}

# =============================================================================
# Validation
# =============================================================================
echo -e "${BLUE}=== Backup Verification ===${NC}"
echo ""

# Check if backup path is provided
if [ -z "$BACKUP_PATH" ]; then
    echo -e "${RED}Error: Backup path is required${NC}"
    echo "Usage: ./verify-backup.sh --backup BACKUP_PATH"
    exit 1
fi

# Check if backup exists
if [ ! -e "$BACKUP_PATH" ]; then
    echo -e "${RED}Error: Backup not found: $BACKUP_PATH${NC}"
    exit 1
fi

# =============================================================================
# Extract Backup (if compressed)
# =============================================================================
BACKUP_DIR=""
TEMP_DIR=""

if [[ "$BACKUP_PATH" == *.tar.gz ]]; then
    echo "1. Extracting backup..."
    
    TEMP_DIR="/tmp/verify-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$TEMP_DIR"
    
    tar xzf "$BACKUP_PATH" -C "$TEMP_DIR" 2>/dev/null
    check $? "Backup extracted"
    
    # Find the backup directory
    BACKUP_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "pos-erp-backup-*" | head -1)
    
    if [ -z "$BACKUP_DIR" ]; then
        echo -e "${RED}Error: Could not find backup directory in archive${NC}"
        exit 1
    fi
    
    info "Extracted to: $BACKUP_DIR"
else
    BACKUP_DIR="$BACKUP_PATH"
fi

echo ""

# =============================================================================
# 2. Check Required Files
# =============================================================================
echo "2. Checking required files..."

# Database
if [ -f "$BACKUP_DIR/pos_erp.db" ]; then
    check 0 "Database file exists"
    
    # Check file size
    DB_SIZE=$(stat -f%z "$BACKUP_DIR/pos_erp.db" 2>/dev/null || stat -c%s "$BACKUP_DIR/pos_erp.db" 2>/dev/null)
    if [ "$DB_SIZE" -gt 0 ]; then
        check 0 "Database file is not empty"
        info "Database size: $(du -h "$BACKUP_DIR/pos_erp.db" | cut -f1)"
    else
        check 1 "Database file is not empty"
    fi
else
    check 1 "Database file exists"
fi

# Environment file
if [ -f "$BACKUP_DIR/.env" ]; then
    check 0 "Environment file exists"
    
    # Check file size
    ENV_SIZE=$(stat -f%z "$BACKUP_DIR/.env" 2>/dev/null || stat -c%s "$BACKUP_DIR/.env" 2>/dev/null)
    if [ "$ENV_SIZE" -gt 0 ]; then
        check 0 "Environment file is not empty"
        info "Environment size: $(du -h "$BACKUP_DIR/.env" | cut -f1)"
    else
        check 1 "Environment file is not empty"
    fi
else
    check 1 "Environment file exists"
fi

# Manifest
if [ -f "$BACKUP_DIR/MANIFEST.md" ]; then
    check 0 "Manifest file exists"
else
    warn "Manifest file missing (optional)"
fi

echo ""

# =============================================================================
# 3. Check Optional Files
# =============================================================================
echo "3. Checking optional files..."

# Nginx config
if [ -f "$BACKUP_DIR/nginx-pos-erp.conf" ]; then
    check 0 "Nginx configuration exists"
else
    warn "Nginx configuration missing (optional)"
fi

# Systemd service
if [ -f "$BACKUP_DIR/pos-erp.service" ]; then
    check 0 "Systemd service exists"
else
    warn "Systemd service missing (optional)"
fi

# SSL certificates
if [ -d "$BACKUP_DIR/ssl" ]; then
    check 0 "SSL certificates exist"
else
    warn "SSL certificates missing (optional)"
fi

# Git bundle
if [ -f "$BACKUP_DIR/repo.bundle" ]; then
    check 0 "Git repository bundle exists"
else
    warn "Git repository bundle missing (optional)"
fi

# Scripts
if [ -d "$BACKUP_DIR/scripts" ]; then
    check 0 "Scripts directory exists"
else
    warn "Scripts directory missing (optional)"
fi

echo ""

# =============================================================================
# 4. Verify Database Integrity
# =============================================================================
echo "4. Verifying database integrity..."

if [ -f "$BACKUP_DIR/pos_erp.db" ]; then
    # Integrity check
    INTEGRITY=$(sqlite3 "$BACKUP_DIR/pos_erp.db" "PRAGMA integrity_check;" 2>/dev/null)
    if [ "$INTEGRITY" = "ok" ]; then
        check 0 "Database integrity check"
    else
        check 1 "Database integrity check"
        info "Integrity result: $INTEGRITY"
    fi
    
    # Foreign key check
    FK_ERRORS=$(sqlite3 "$BACKUP_DIR/pos_erp.db" "PRAGMA foreign_key_check;" 2>/dev/null | wc -l)
    if [ "$FK_ERRORS" -eq 0 ]; then
        check 0 "Foreign key integrity"
    else
        warn "Foreign key errors: $FK_ERRORS"
    fi
    
    # Check tables
    echo ""
    echo "5. Checking database tables..."
    
    TABLES=$(sqlite3 "$BACKUP_DIR/pos_erp.db" ".tables" 2>/dev/null)
    REQUIRED_TABLES="branch users product txn"
    
    for table in $REQUIRED_TABLES; do
        if echo "$TABLES" | grep -q "$table"; then
            COUNT=$(sqlite3 "$BACKUP_DIR/pos_erp.db" "SELECT COUNT(*) FROM $table;" 2>/dev/null)
            check 0 "Table '$table' exists ($COUNT records)"
        else
            check 1 "Table '$table' exists"
        fi
    done
    
    # Show database stats
    echo ""
    echo "6. Database statistics..."
    
    BRANCH_COUNT=$(sqlite3 "$BACKUP_DIR/pos_erp.db" "SELECT COUNT(*) FROM branch;" 2>/dev/null)
    USER_COUNT=$(sqlite3 "$BACKUP_DIR/pos_erp.db" "SELECT COUNT(*) FROM users;" 2>/dev/null)
    PRODUCT_COUNT=$(sqlite3 "$BACKUP_DIR/pos_erp.db" "SELECT COUNT(*) FROM product;" 2>/dev/null)
    TXN_COUNT=$(sqlite3 "$BACKUP_DIR/pos_erp.db" "SELECT COUNT(*) FROM txn;" 2>/dev/null)
    
    echo -e "  📊 Branches: $BRANCH_COUNT"
    echo -e "  📊 Users: $USER_COUNT"
    echo -e "  📊 Products: $PRODUCT_COUNT"
    echo -e "  📊 Transactions: $TXN_COUNT"
fi

echo ""

# =============================================================================
# 5. Verify Environment File
# =============================================================================
echo "7. Verifying environment file..."

if [ -f "$BACKUP_DIR/.env" ]; then
    # Check for required variables
    REQUIRED_VARS="POS_ERP_DB_PATH POS_ERP_SECRET_KEY"
    
    for var in $REQUIRED_VARS; do
        if grep -q "^$var=" "$BACKUP_DIR/.env"; then
            check 0 "Variable '$var' exists"
        else
            warn "Variable '$var' missing"
        fi
    done
    
    # Check for sensitive data (should not be empty)
    if grep -q "POS_ERP_SECRET_KEY=" "$BACKUP_DIR/.env"; then
        SECRET_KEY=$(grep "POS_ERP_SECRET_KEY=" "$BACKUP_DIR/.env" | cut -d'=' -f2)
        if [ -n "$SECRET_KEY" ] && [ "$SECRET_KEY" != "" ]; then
            check 0 "Secret key is not empty"
        else
            check 1 "Secret key is not empty"
        fi
    fi
fi

echo ""

# =============================================================================
# 6. Check Backup Size
# =============================================================================
echo "8. Checking backup size..."

BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo -e "  📦 Total backup size: $BACKUP_SIZE"

# Check individual file sizes
if [ -f "$BACKUP_DIR/pos_erp.db" ]; then
    DB_SIZE=$(du -h "$BACKUP_DIR/pos_erp.db" | cut -f1)
    echo -e "  📦 Database size: $DB_SIZE"
fi

if [ -f "$BACKUP_DIR/.env" ]; then
    ENV_SIZE=$(du -h "$BACKUP_DIR/.env" | cut -f1)
    echo -e "  📦 Environment size: $ENV_SIZE"
fi

if [ -f "$BACKUP_DIR/repo.bundle" ]; then
    REPO_SIZE=$(du -h "$BACKUP_DIR/repo.bundle" | cut -f1)
    echo -e "  📦 Repository size: $REPO_SIZE"
fi

echo ""

# =============================================================================
# 7. Check Backup Age
# =============================================================================
echo "9. Checking backup age..."

if [ -f "$BACKUP_DIR/MANIFEST.md" ]; then
    BACKUP_DATE=$(grep "Created:" "$BACKUP_DIR/MANIFEST.md" | cut -d':' -f2- | xargs)
    echo -e "  📅 Backup created: $BACKUP_DATE"
    
    # Calculate age in days
    if command -v date &> /dev/null; then
        BACKUP_TIMESTAMP=$(date -d "$BACKUP_DATE" +%s 2>/dev/null || date -j -f "%Y-%m-%d %H:%M:%S" "$BACKUP_DATE" +%s 2>/dev/null)
        CURRENT_TIMESTAMP=$(date +%s)
        
        if [ -n "$BACKUP_TIMESTAMP" ]; then
            AGE_DAYS=$(( (CURRENT_TIMESTAMP - BACKUP_TIMESTAMP) / 86400 ))
            echo -e "  📅 Backup age: $AGE_DAYS days"
            
            if [ $AGE_DAYS -gt 7 ]; then
                warn "Backup is older than 7 days"
            else
                check 0 "Backup is recent"
            fi
        fi
    fi
fi

echo ""

# =============================================================================
# Cleanup
# =============================================================================
if [ -n "$TEMP_DIR" ]; then
    rm -rf "$TEMP_DIR"
fi

# =============================================================================
# Summary
# =============================================================================
echo -e "${BLUE}=== Verification Summary ===${NC}"
echo ""
echo -e "  ${GREEN}Passed: $PASS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"
echo -e "  ${YELLOW}Warnings: $WARN${NC}"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Backup verification PASSED${NC}"
    echo ""
    echo "This backup is ready for restore."
    echo "To restore:"
    echo "  ./restore-full.sh --backup $BACKUP_PATH"
    exit 0
else
    echo ""
    echo -e "${RED}✗ Backup verification FAILED${NC}"
    echo ""
    echo "This backup may not restore correctly."
    echo "Please check the errors above and create a new backup."
    exit 1
fi
