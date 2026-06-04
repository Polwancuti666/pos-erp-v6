#!/bin/bash
# =============================================================================
# Beauty & Shine ERP — Complete Backup Script
# =============================================================================
# Backs up everything needed to restore the system on any VPS:
#   - Database (SQLite)
#   - Environment file (.env)
#   - Nginx configuration
#   - Systemd service file
#   - Application code (optional)
#   - SSL certificates (optional)
#
# Usage:
#   ./backup-full.sh [OPTIONS]
#
# Options:
#   --output DIR     Backup output directory (default: /var/www/pos-erp-v6/backups)
#   --keep DAYS      Days to keep old backups (default: 30)
#   --compress       Compress backup (default: yes)
#   --upload         Upload to remote storage (not implemented yet)
#   --quiet          Suppress output
#
# Cron example:
#   0 2 * * * /var/www/pos-erp-v6/scripts/backup/backup-full.sh --quiet
# =============================================================================

set -e

# =============================================================================
# Configuration
# =============================================================================
APP_DIR="/var/www/pos-erp-v6"
DB_PATH="$APP_DIR/pos_erp.db"
ENV_PATH="$APP_DIR/.env"
NGINX_CONF="/etc/nginx/sites-available/pos-erp"
SYSTEMD_CONF="/etc/systemd/system/pos-erp.service"
BACKUP_DIR="$APP_DIR/backups"
KEEP_DAYS=30
COMPRESS=true
UPLOAD=false
QUIET=false
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="pos-erp-backup-${TIMESTAMP}"
LOG_FILE="$BACKUP_DIR/backup.log"

# =============================================================================
# Parse Arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --output)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --keep)
            KEEP_DAYS="$2"
            shift 2
            ;;
        --no-compress)
            COMPRESS=false
            shift
            ;;
        --upload)
            UPLOAD=true
            shift
            ;;
        --quiet)
            QUIET=true
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
    if [ "$QUIET" = false ]; then
        echo "$1"
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

# =============================================================================
# Pre-Backup Checks
# =============================================================================
log "=== Starting Full Backup ==="
log "Timestamp: $TIMESTAMP"
log "Backup name: $BACKUP_NAME"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    error_exit "Database not found: $DB_PATH"
fi

# Check if .env exists
if [ ! -f "$ENV_PATH" ]; then
    error_exit "Environment file not found: $ENV_PATH"
fi

# =============================================================================
# 1. Backup Database
# =============================================================================
log ""
log "1. Backing up database..."

# Stop application briefly for consistent backup
systemctl stop pos-erp 2>/dev/null || true
sleep 2

# Copy database
cp "$DB_PATH" "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db"

# Verify integrity
INTEGRITY=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db" "PRAGMA integrity_check;")
if [ "$INTEGRITY" = "ok" ]; then
    log "   ✓ Database integrity: OK"
else
    error_exit "Database integrity check failed: $INTEGRITY"
fi

# Get database stats
BRANCH_COUNT=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db" "SELECT COUNT(*) FROM branch;")
USER_COUNT=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db" "SELECT COUNT(*) FROM users;")
PRODUCT_COUNT=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db" "SELECT COUNT(*) FROM product;")
TXN_COUNT=$(sqlite3 "$BACKUP_DIR/$BACKUP_NAME/pos_erp.db" "SELECT COUNT(*) FROM txn;")

log "   📊 Branches: $BRANCH_COUNT"
log "   📊 Users: $USER_COUNT"
log "   📊 Products: $PRODUCT_COUNT"
log "   📊 Transactions: $TXN_COUNT"

# Restart application
systemctl start pos-erp 2>/dev/null || true

# =============================================================================
# 2. Backup Environment File
# =============================================================================
log ""
log "2. Backing up environment file..."

cp "$ENV_PATH" "$BACKUP_DIR/$BACKUP_NAME/.env"

# Verify .env is not empty
if [ -s "$BACKUP_DIR/$BACKUP_NAME/.env" ]; then
    ENV_LINES=$(wc -l < "$BACKUP_DIR/$BACKUP_NAME/.env")
    log "   ✓ .env backed up ($ENV_LINES lines)"
else
    error_exit ".env file is empty"
fi

# =============================================================================
# 3. Backup Nginx Configuration
# =============================================================================
log ""
log "3. Backing up Nginx configuration..."

if [ -f "$NGINX_CONF" ]; then
    cp "$NGINX_CONF" "$BACKUP_DIR/$BACKUP_NAME/nginx-pos-erp.conf"
    log "   ✓ Nginx config backed up"
else
    log "   ⚠ Nginx config not found (skipping)"
fi

# =============================================================================
# 4. Backup Systemd Service
# =============================================================================
log ""
log "4. Backing up Systemd service..."

if [ -f "$SYSTEMD_CONF" ]; then
    cp "$SYSTEMD_CONF" "$BACKUP_DIR/$BACKUP_NAME/pos-erp.service"
    log "   ✓ Systemd service backed up"
else
    log "   ⚠ Systemd service not found (skipping)"
fi

# =============================================================================
# 5. Backup SSL Certificates (Optional)
# =============================================================================
log ""
log "5. Backing up SSL certificates..."

SSL_DIR="/etc/letsencrypt/live/beautynshine.web.id"
if [ -d "$SSL_DIR" ]; then
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME/ssl"
    cp -r "$SSL_DIR" "$BACKUP_DIR/$BACKUP_NAME/ssl/"
    log "   ✓ SSL certificates backed up"
else
    log "   ⚠ SSL certificates not found (skipping)"
fi

# =============================================================================
# 6. Backup Application Code (Optional)
# =============================================================================
log ""
log "6. Backing up application code..."

# Create git bundle for full repo backup
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    git bundle create "$BACKUP_DIR/$BACKUP_NAME/repo.bundle" main 2>/dev/null || true
    if [ -f "$BACKUP_DIR/$BACKUP_NAME/repo.bundle" ]; then
        log "   ✓ Git repository bundled"
    else
        log "   ⚠ Git bundle failed (skipping)"
    fi
fi

# =============================================================================
# 7. Backup Scripts
# =============================================================================
log ""
log "7. Backing up scripts..."

if [ -d "$APP_DIR/scripts" ]; then
    cp -r "$APP_DIR/scripts" "$BACKUP_DIR/$BACKUP_NAME/scripts"
    log "   ✓ Scripts backed up"
fi

# =============================================================================
# 8. Create Backup Manifest
# =============================================================================
log ""
log "8. Creating backup manifest..."

cat > "$BACKUP_DIR/$BACKUP_NAME/MANIFEST.md" << EOF
# Backup Manifest

**Created:** $(date '+%Y-%m-%d %H:%M:%S')
**Hostname:** $(hostname)
**Backup Name:** $BACKUP_NAME

## Contents

| File | Description | Status |
|------|-------------|--------|
| pos_erp.db | SQLite database | ✓ |
| .env | Environment variables | ✓ |
| nginx-pos-erp.conf | Nginx configuration | $([ -f "$BACKUP_DIR/$BACKUP_NAME/nginx-pos-erp.conf" ] && echo "✓" || echo "⚠ Missing") |
| pos-erp.service | Systemd service | $([ -f "$BACKUP_DIR/$BACKUP_NAME/pos-erp.service" ] && echo "✓" || echo "⚠ Missing") |
| ssl/ | SSL certificates | $([ -d "$BACKUP_DIR/$BACKUP_NAME/ssl" ] && echo "✓" || echo "⚠ Missing") |
| repo.bundle | Git repository | $([ -f "$BACKUP_DIR/$BACKUP_NAME/repo.bundle" ] && echo "✓" || echo "⚠ Missing") |
| scripts/ | Application scripts | $([ -d "$BACKUP_DIR/$BACKUP_NAME/scripts" ] && echo "✓" || echo "⚠ Missing") |

## Database Statistics

- Branches: $BRANCH_COUNT
- Users: $USER_COUNT
- Products: $PRODUCT_COUNT
- Transactions: $TXN_COUNT

## Restore Instructions

1. Copy backup to new VPS
2. Run: \`./scripts/backup/restore-full.sh --backup $BACKUP_DIR/$BACKUP_NAME\`
3. Or follow: \`docs/migration/02-database-migration.md\`

## Verification

\`\`\`bash
# Verify database integrity
sqlite3 pos_erp.db "PRAGMA integrity_check;"

# Verify .env exists
cat .env | head -5
\`\`\`
EOF

log "   ✓ Manifest created"

# =============================================================================
# 9. Compress Backup (Optional)
# =============================================================================
if [ "$COMPRESS" = true ]; then
    log ""
    log "9. Compressing backup..."
    
    cd "$BACKUP_DIR"
    tar czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
    
    # Calculate sizes
    ORIGINAL_SIZE=$(du -sh "$BACKUP_NAME" | cut -f1)
    COMPRESSED_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
    
    log "   ✓ Compressed: $ORIGINAL_SIZE → $COMPRESSED_SIZE"
    
    # Remove uncompressed directory
    rm -rf "$BACKUP_NAME"
fi

# =============================================================================
# 10. Cleanup Old Backups
# =============================================================================
log ""
log "10. Cleaning up old backups (keeping last $KEEP_DAYS days)..."

DELETED=0
if [ "$COMPRESS" = true ]; then
    find "$BACKUP_DIR" -name "pos-erp-backup-*.tar.gz" -mtime +$KEEP_DAYS -delete -print | while read -r file; do
        log "   🗑 Deleted: $(basename "$file")"
        ((DELETED++))
    done
else
    find "$BACKUP_DIR" -name "pos-erp-backup-*" -type d -mtime +$KEEP_DAYS -exec rm -rf {} \; -print | while read -r dir; do
        log "   🗑 Deleted: $(basename "$dir")"
        ((DELETED++))
    done
fi

log "   ✓ Cleanup complete"

# =============================================================================
# Summary
# =============================================================================
log ""
log "=== Backup Complete ==="
log ""
log "Backup location: $BACKUP_DIR"

if [ "$COMPRESS" = true ]; then
    BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}.tar.gz"
    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    log "Backup file: ${BACKUP_NAME}.tar.gz"
    log "Backup size: $BACKUP_SIZE"
else
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_NAME"
    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    log "Backup directory: $BACKUP_NAME"
    log "Backup size: $BACKUP_SIZE"
fi

log ""
log "To restore on a new VPS:"
log "  1. Copy backup to new VPS"
log "  2. Run: ./scripts/backup/restore-full.sh --backup $BACKUP_FILE"
log ""

# Output backup path for automation
if [ "$QUIET" = true ]; then
    echo "$BACKUP_FILE"
fi
