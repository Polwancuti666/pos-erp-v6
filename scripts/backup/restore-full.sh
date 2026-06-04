#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — Complete Restore Script
# =============================================================================
# Restores a full backup on a new VPS.
#
# Usage:
#   ./restore-full.sh --backup BACKUP_PATH [OPTIONS]
#
# Options:
#   --backup PATH    Path to backup file (.tar.gz) or directory
#   --domain DOMAIN  Domain name (default: beautynshine.web.id)
#   --skip-ssl       Skip SSL certificate restore
#   --skip-nginx     Skip Nginx configuration restore
#   --skip-systemd   Skip Systemd service restore
#   --dry-run        Show what would be done without making changes
#   --yes            Skip confirmation prompts
#
# Examples:
#   ./restore-full.sh --backup /tmp/pos-erp-backup-20260604_020000.tar.gz
#   ./restore-full.sh --backup /tmp/pos-erp-backup-20260604_020000 --dry-run
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================
APP_DIR="/var/www/pos-erp-v6"
BACKUP_PATH=""
DOMAIN="beautynshine.web.id"
SKIP_SSL=false
SKIP_NGINX=false
SKIP_SYSTEMD=false
DRY_RUN=false
AUTO_YES=false
RESTORE_LOG="/tmp/restore-$(date +%Y%m%d_%H%M%S).log"

# =============================================================================
# Colors
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --backup)
            BACKUP_PATH="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --skip-ssl)
            SKIP_SSL=true
            shift
            ;;
        --skip-nginx)
            SKIP_NGINX=true
            shift
            ;;
        --skip-systemd)
            SKIP_SYSTEMD=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --yes)
            AUTO_YES=true
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
log() {
    echo -e "$1" | tee -a "$RESTORE_LOG"
}

error_exit() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

confirm() {
    if [ "$AUTO_YES" = true ]; then
        return 0
    fi
    
    read -p "$1 [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}[DRY RUN]${NC} $1"
    else
        log "   Running: $1"
        eval "$1" 2>&1 | tee -a "$RESTORE_LOG"
    fi
}

# =============================================================================
# Validation
# =============================================================================
log "${BLUE}=== Beauty & Shine ERP — Full Restore ===${NC}"
log ""
log "Restore log: $RESTORE_LOG"
log ""

# Check if backup path is provided
if [ -z "$BACKUP_PATH" ]; then
    error_exit "Backup path is required. Use --backup PATH"
fi

# Check if backup exists
if [ ! -e "$BACKUP_PATH" ]; then
    error_exit "Backup not found: $BACKUP_PATH"
fi

# =============================================================================
# Extract Backup (if compressed)
# =============================================================================
BACKUP_DIR=""
if [[ "$BACKUP_PATH" == *.tar.gz ]]; then
    log "1. Extracting backup..."
    
    EXTRACT_DIR="/tmp/restore-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$EXTRACT_DIR"
    
    run_cmd "tar xzf '$BACKUP_PATH' -C '$EXTRACT_DIR'"
    
    # Find the backup directory
    BACKUP_DIR=$(find "$EXTRACT_DIR" -maxdepth 1 -type d -name "pos-erp-backup-*" | head -1)
    
    if [ -z "$BACKUP_DIR" ]; then
        error_exit "Could not find backup directory in archive"
    fi
    
    log "   ✓ Extracted to: $BACKUP_DIR"
else
    BACKUP_DIR="$BACKUP_PATH"
fi

# Verify backup directory
if [ ! -d "$BACKUP_DIR" ]; then
    error_exit "Backup directory not found: $BACKUP_DIR"
fi

# Check for required files
if [ ! -f "$BACKUP_DIR/pos_erp.db" ]; then
    error_exit "Database file not found in backup"
fi

if [ ! -f "$BACKUP_DIR/.env" ]; then
    error_exit "Environment file not found in backup"
fi

# Show backup manifest
if [ -f "$BACKUP_DIR/MANIFEST.md" ]; then
    log ""
    log "2. Backup manifest:"
    cat "$BACKUP_DIR/MANIFEST.md" | head -30
    log ""
fi

# Confirmation
if [ "$DRY_RUN" = false ]; then
    log "${YELLOW}WARNING: This will overwrite existing files!${NC}"
    log ""
    log "The following will be restored:"
    log "  - Database: $APP_DIR/pos_erp.db"
    log "  - Environment: $APP_DIR/.env"
    
    if [ "$SKIP_NGINX" = false ] && [ -f "$BACKUP_DIR/nginx-pos-erp.conf" ]; then
        log "  - Nginx: /etc/nginx/sites-available/pos-erp"
    fi
    
    if [ "$SKIP_SYSTEMD" = false ] && [ -f "$BACKUP_DIR/pos-erp.service" ]; then
        log "  - Systemd: /etc/systemd/system/pos-erp.service"
    fi
    
    if [ "$SKIP_SSL" = false ] && [ -d "$BACKUP_DIR/ssl" ]; then
        log "  - SSL: /etc/letsencrypt/"
    fi
    
    log ""
    
    if ! confirm "Do you want to continue?"; then
        log "Restore cancelled."
        exit 0
    fi
fi

# =============================================================================
# 3. Stop Services
# =============================================================================
log ""
log "3. Stopping services..."

run_cmd "systemctl stop pos-erp 2>/dev/null || true"
run_cmd "systemctl stop nginx 2>/dev/null || true"

log "   ✓ Services stopped"

# =============================================================================
# 4. Create Application Directory
# =============================================================================
log ""
log "4. Creating application directory..."

run_cmd "mkdir -p '$APP_DIR'/{logs,backups,static}"
run_cmd "chown -R deploy:deploy '$APP_DIR'"

log "   ✓ Directory structure created"

# =============================================================================
# 5. Restore Database
# =============================================================================
log ""
log "5. Restoring database..."

# Backup existing database (if exists)
if [ -f "$APP_DIR/pos_erp.db" ]; then
    run_cmd "cp '$APP_DIR/pos_erp.db' '$APP_DIR/pos_erp.db.backup.$(date +%Y%m%d_%H%M%S)'"
    log "   ✓ Existing database backed up"
fi

# Restore database
run_cmd "cp '$BACKUP_DIR/pos_erp.db' '$APP_DIR/pos_erp.db'"
run_cmd "chmod 664 '$APP_DIR/pos_erp.db'"
run_cmd "chown deploy:deploy '$APP_DIR/pos_erp.db'"

# Verify integrity
if [ "$DRY_RUN" = false ]; then
    INTEGRITY=$(sqlite3 "$APP_DIR/pos_erp.db" "PRAGMA integrity_check;")
    if [ "$INTEGRITY" = "ok" ]; then
        log "   ✓ Database integrity: OK"
    else
        error_exit "Database integrity check failed"
    fi
    
    # Show stats
    BRANCH_COUNT=$(sqlite3 "$APP_DIR/pos_erp.db" "SELECT COUNT(*) FROM branch;")
    USER_COUNT=$(sqlite3 "$APP_DIR/pos_erp.db" "SELECT COUNT(*) FROM users;")
    PRODUCT_COUNT=$(sqlite3 "$APP_DIR/pos_erp.db" "SELECT COUNT(*) FROM product;")
    TXN_COUNT=$(sqlite3 "$APP_DIR/pos_erp.db" "SELECT COUNT(*) FROM txn;")
    
    log "   📊 Branches: $BRANCH_COUNT"
    log "   📊 Users: $USER_COUNT"
    log "   📊 Products: $PRODUCT_COUNT"
    log "   📊 Transactions: $TXN_COUNT"
fi

# =============================================================================
# 6. Restore Environment File
# =============================================================================
log ""
log "6. Restoring environment file..."

# Backup existing .env (if exists)
if [ -f "$APP_DIR/.env" ]; then
    run_cmd "cp '$APP_DIR/.env' '$APP_DIR/.env.backup.$(date +%Y%m%d_%H%M%S)'"
    log "   ✓ Existing .env backed up"
fi

# Restore .env
run_cmd "cp '$BACKUP_DIR/.env' '$APP_DIR/.env'"
run_cmd "chmod 600 '$APP_DIR/.env'"
run_cmd "chown deploy:deploy '$APP_DIR/.env'"

log "   ✓ Environment file restored"

# =============================================================================
# 7. Restore Nginx Configuration
# =============================================================================
if [ "$SKIP_NGINX" = false ] && [ -f "$BACKUP_DIR/nginx-pos-erp.conf" ]; then
    log ""
    log "7. Restoring Nginx configuration..."
    
    run_cmd "cp '$BACKUP_DIR/nginx-pos-erp.conf' /etc/nginx/sites-available/pos-erp"
    run_cmd "ln -sf /etc/nginx/sites-available/pos-erp /etc/nginx/sites-enabled/"
    run_cmd "rm -f /etc/nginx/sites-enabled/default"
    
    # Update domain if different
    if [ "$DOMAIN" != "beautynshine.web.id" ]; then
        run_cmd "sed -i 's/beautynshine.web.id/$DOMAIN/g' /etc/nginx/sites-available/pos-erp"
        log "   ✓ Domain updated to: $DOMAIN"
    fi
    
    log "   ✓ Nginx configuration restored"
else
    log ""
    log "7. Skipping Nginx configuration..."
fi

# =============================================================================
# 8. Restore Systemd Service
# =============================================================================
if [ "$SKIP_SYSTEMD" = false ] && [ -f "$BACKUP_DIR/pos-erp.service" ]; then
    log ""
    log "8. Restoring Systemd service..."
    
    run_cmd "cp '$BACKUP_DIR/pos-erp.service' /etc/systemd/system/pos-erp.service"
    run_cmd "systemctl daemon-reload"
    run_cmd "systemctl enable pos-erp"
    
    log "   ✓ Systemd service restored"
else
    log ""
    log "8. Skipping Systemd service..."
fi

# =============================================================================
# 9. Restore SSL Certificates
# =============================================================================
if [ "$SKIP_SSL" = false ] && [ -d "$BACKUP_DIR/ssl" ]; then
    log ""
    log "9. Restoring SSL certificates..."
    
    run_cmd "mkdir -p /etc/letsencrypt/live/"
    run_cmd "cp -r '$BACKUP_DIR/ssl/'* /etc/letsencrypt/live/"
    
    log "   ✓ SSL certificates restored"
else
    log ""
    log "9. Skipping SSL certificates..."
fi

# =============================================================================
# 10. Clone Repository (if not exists)
# =============================================================================
log ""
log "10. Setting up application code..."

if [ ! -d "$APP_DIR/.git" ]; then
    if [ -f "$BACKUP_DIR/repo.bundle" ]; then
        log "   Restoring from bundle..."
        run_cmd "cd '$APP_DIR' && git clone '$BACKUP_DIR/repo.bundle' ."
    else
        log "   Cloning from GitHub..."
        run_cmd "cd '$APP_DIR' && git clone https://github.com/Polwancuti666/pos-erp-v6.git ."
    fi
else
    log "   ✓ Application code already exists"
fi

# =============================================================================
# 11. Setup Python Environment
# =============================================================================
log ""
log "11. Setting up Python environment..."

if [ ! -d "$APP_DIR/.venv" ]; then
    run_cmd "cd '$APP_DIR' && python3.11 -m venv .venv"
    run_cmd "cd '$APP_DIR' && source .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn uvicorn[standard]"
    log "   ✓ Python environment created"
else
    log "   ✓ Python environment already exists"
fi

# =============================================================================
# 12. Build Frontend
# =============================================================================
log ""
log "12. Building frontend..."

if [ ! -d "$APP_DIR/frontend/dist" ]; then
    run_cmd "cd '$APP_DIR/frontend' && npm ci && npm run build"
    run_cmd "cp -r '$APP_DIR/frontend/dist/'* '$APP_DIR/static/'"
    log "   ✓ Frontend built"
else
    log "   ✓ Frontend already built"
fi

# =============================================================================
# 13. Restore Scripts
# =============================================================================
if [ -d "$BACKUP_DIR/scripts" ]; then
    log ""
    log "13. Restoring scripts..."
    
    run_cmd "cp -r '$BACKUP_DIR/scripts/'* '$APP_DIR/scripts/'"
    run_cmd "chmod +x '$APP_DIR/scripts/'*.sh"
    
    log "   ✓ Scripts restored"
fi

# =============================================================================
# 14. Set Permissions
# =============================================================================
log ""
log "14. Setting permissions..."

run_cmd "chown -R deploy:deploy '$APP_DIR'"
run_cmd "chmod -R 755 '$APP_DIR'"
run_cmd "chmod 600 '$APP_DIR/.env'"
run_cmd "chmod 664 '$APP_DIR/pos_erp.db'"

log "   ✓ Permissions set"

# =============================================================================
# 15. Start Services
# =============================================================================
log ""
log "15. Starting services..."

if [ "$DRY_RUN" = false ]; then
    run_cmd "systemctl start pos-erp"
    sleep 3
    run_cmd "systemctl start nginx"
    
    # Check services
    if systemctl is-active pos-erp > /dev/null 2>&1; then
        log "   ✓ pos-erp service: ACTIVE"
    else
        log "   ✗ pos-erp service: FAILED"
        log "   Check logs: journalctl -u pos-erp -n 50"
    fi
    
    if systemctl is-active nginx > /dev/null 2>&1; then
        log "   ✓ nginx service: ACTIVE"
    else
        log "   ✗ nginx service: FAILED"
        log "   Check logs: journalctl -u nginx -n 50"
    fi
fi

# =============================================================================
# 16. Verify Restore
# =============================================================================
log ""
log "16. Verifying restore..."

if [ "$DRY_RUN" = false ]; then
    # Test health endpoint
    sleep 2
    HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo "FAILED")
    
    if echo "$HEALTH" | grep -q "ok"; then
        log "   ✓ API health: OK"
    else
        log "   ⚠ API health: FAILED (may need time to start)"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
log ""
log "${GREEN}=== Restore Complete ===${NC}"
log ""
log "Application directory: $APP_DIR"
log "Database: $APP_DIR/pos_erp.db"
log "Environment: $APP_DIR/.env"
log "Logs: $APP_DIR/logs/"
log ""
log "Next steps:"
log "  1. Verify application: curl http://localhost:8000/health"
log "  2. Check logs: journalctl -u pos-erp -f"
log "  3. Setup SSL (if needed): certbot --nginx -d $DOMAIN"
log "  4. Update DNS: Point $DOMAIN to this server's IP"
log ""
log "Restore log saved to: $RESTORE_LOG"
